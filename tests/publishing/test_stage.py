import json
from pathlib import Path

import pytest

from compiler_engine.canonical_knowledge_object_generation.stage import CkoGenerationStage
from compiler_engine.core.config import CompilerConfig
from compiler_engine.core.errors import CompilerError
from compiler_engine.domain.taxonomy import Taxonomy, TaxonomyNode
from compiler_engine.educational_analysis.stage import EducationalAnalysisStage
from compiler_engine.paper_import.stage import PaperImportStage
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.pipeline.runner import PipelineRunner
from compiler_engine.pipeline.stage import StageStatus
from compiler_engine.publishing.models import ExportManifest, ExportStatistics
from compiler_engine.publishing.stage import PublishingStage
from compiler_engine.relationship_resolution.stage import RelationshipResolutionStage

REAL_PAPER_PATH = Path(__file__).resolve().parents[2] / "imports" / "paper.json"
REAL_TAXONOMY_PATH = Path(__file__).resolve().parents[2] / "reference" / "taxonomy.json"


def _context(tmp_path) -> CompilerContext:
    config = CompilerConfig(
        import_workspace=tmp_path / "import",
        assets_folder=tmp_path / "assets",
        output_folder=tmp_path / "output",
    )
    return CompilerContext.create(config)


def test_validate_inputs_requires_a_registered_cko(tmp_path):
    with pytest.raises(CompilerError):
        PublishingStage().validate_inputs(_context(tmp_path))


def _real_curriculum_taxonomies() -> tuple[Taxonomy, Taxonomy]:
    data = json.loads(REAL_TAXONOMY_PATH.read_text(encoding="utf-8"))

    def concept_node(c):
        return TaxonomyNode(node_id=c["id"], name=c["name"], level=3)

    def topic_node(t):
        return TaxonomyNode(node_id=t["id"], name=t["name"], level=2,
                             children=tuple(concept_node(c) for c in t.get("concepts", [])))

    def chapter_node(c):
        return TaxonomyNode(node_id=c["id"], name=c["name"], level=1,
                             children=tuple(topic_node(t) for t in c.get("topics", [])))

    def unit_node(u):
        return TaxonomyNode(node_id=u["id"], name=u["name"], level=0,
                             children=tuple(chapter_node(c) for c in u.get("chapters", [])))

    curriculum = Taxonomy(taxonomy_id="curriculum", name="real",
                           roots=tuple(unit_node(u) for u in data["curriculum"]))
    question_types = Taxonomy(
        taxonomy_id="question_types", name="real qt",
        roots=tuple(TaxonomyNode(node_id=qt["id"], name=qt["name"], level=0) for qt in data["question_types"]),
    )
    return curriculum, question_types, data["metadata"]["taxonomy_version"]


def _run_full_pipeline(tmp_path):
    if not REAL_TAXONOMY_PATH.exists():
        pytest.skip("reference/taxonomy.json not present")

    context = _context(tmp_path).for_document(REAL_PAPER_PATH)
    curriculum, question_types, taxonomy_version = _real_curriculum_taxonomies()
    context.registry.register(curriculum, artifact_id="curriculum")
    context.registry.register(question_types, artifact_id="question_types")
    context.state["taxonomy_version"] = taxonomy_version

    runner = PipelineRunner()
    runner.register(PaperImportStage()).register(RelationshipResolutionStage())
    runner.register(EducationalAnalysisStage()).register(CkoGenerationStage())
    runner.register(PublishingStage())
    summary = runner.run(context)
    return context, summary


def test_full_pipeline_publishes_the_real_gold_standard_paper(tmp_path):
    context, summary = _run_full_pipeline(tmp_path)

    assert summary.halted is False
    assert [r.status for r in summary.results] == [StageStatus.SUCCESS] * 5

    export_dir = context.workspace.layout.output_folder / "export"
    assert (export_dir / "manifest.json").is_file()
    assert (export_dir / "statistics.json").is_file()
    assert (export_dir / "ckos.json").is_file()

    manifest = ExportManifest.from_json((export_dir / "manifest.json").read_text())
    assert manifest.taxonomy_version == "1.0"
    assert manifest.paper_count == 1
    assert manifest.question_count == 49
    assert manifest.cko_count == 49
    assert manifest.checksum_algorithm == "sha256"

    statistics = ExportStatistics.from_json((export_dir / "statistics.json").read_text())
    assert statistics.duplicate_questions_merged == 0
    assert statistics.orphan_relationships_skipped == 1
    assert statistics.validation_warnings == 8
    assert statistics.validation_errors == 3

    ckos_payload = json.loads((export_dir / "ckos.json").read_text())
    assert len(ckos_payload) == 49
    assert [entry["cko_id"] for entry in ckos_payload] == sorted(entry["cko_id"] for entry in ckos_payload)


def _strip_timestamps(payload):
    if isinstance(payload, dict):
        return {
            k: _strip_timestamps(v)
            for k, v in payload.items()
            if k not in ("generated_at", "created_at", "updated_at")
        }
    if isinstance(payload, list):
        return [_strip_timestamps(item) for item in payload]
    return payload


def test_export_is_deterministic_across_two_separate_runs(tmp_path):
    _, _ = _run_full_pipeline(tmp_path / "run1")
    _, _ = _run_full_pipeline(tmp_path / "run2")

    export1 = tmp_path / "run1" / "output" / "export"
    export2 = tmp_path / "run2" / "output" / "export"

    for filename in ("manifest.json", "statistics.json", "ckos.json"):
        payload1 = _strip_timestamps(json.loads((export1 / filename).read_text()))
        payload2 = _strip_timestamps(json.loads((export2 / filename).read_text()))
        assert payload1 == payload2, f"{filename} differs beyond timestamps"
