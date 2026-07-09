from pathlib import Path

import pytest

from compiler_engine.canonical_knowledge_object_generation.checksum import compute_checksum
from compiler_engine.canonical_knowledge_object_generation.stage import CkoGenerationStage
from compiler_engine.core.config import CompilerConfig
from compiler_engine.core.errors import CompilerError
from compiler_engine.domain.cko import CKO
from compiler_engine.domain.taxonomy import Taxonomy
from compiler_engine.educational_analysis.stage import EducationalAnalysisStage
from compiler_engine.paper_import.schema import PaperImport
from compiler_engine.paper_import.stage import PaperImportStage
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.pipeline.runner import PipelineRunner
from compiler_engine.pipeline.stage import StageStatus
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


def _register_empty_taxonomies(context: CompilerContext) -> None:
    context.registry.register(Taxonomy(taxonomy_id="curriculum", name="x", roots=()), artifact_id="curriculum")
    context.registry.register(
        Taxonomy(taxonomy_id="question_types", name="x", roots=()), artifact_id="question_types"
    )


def test_validate_inputs_requires_paper_import(tmp_path):
    with pytest.raises(CompilerError):
        CkoGenerationStage().validate_inputs(_context(tmp_path))


def test_validate_inputs_requires_relationship_resolution(tmp_path):
    context = _context(tmp_path).for_document(REAL_PAPER_PATH)
    PaperImportStage().execute(context)
    with pytest.raises(CompilerError):
        CkoGenerationStage().validate_inputs(context)


def test_validate_inputs_requires_educational_analysis(tmp_path):
    context = _context(tmp_path).for_document(REAL_PAPER_PATH)
    PaperImportStage().execute(context)
    RelationshipResolutionStage().execute(context)
    with pytest.raises(CompilerError):
        CkoGenerationStage().validate_inputs(context)


def test_full_pipeline_on_real_gold_standard_paper_and_taxonomy(tmp_path):
    if not REAL_TAXONOMY_PATH.exists():
        pytest.skip("reference/taxonomy.json not present")

    import json

    from compiler_engine.domain.taxonomy import TaxonomyNode

    taxonomy_data = json.loads(REAL_TAXONOMY_PATH.read_text(encoding="utf-8"))

    def concept_node(c):
        return TaxonomyNode(node_id=c["id"], name=c["name"], level=3)

    def topic_node(t):
        return TaxonomyNode(
            node_id=t["id"], name=t["name"], level=2,
            children=tuple(concept_node(c) for c in t.get("concepts", [])),
        )

    def chapter_node(c):
        return TaxonomyNode(
            node_id=c["id"], name=c["name"], level=1,
            children=tuple(topic_node(t) for t in c.get("topics", [])),
        )

    def unit_node(u):
        return TaxonomyNode(
            node_id=u["id"], name=u["name"], level=0,
            children=tuple(chapter_node(c) for c in u.get("chapters", [])),
        )

    curriculum = Taxonomy(
        taxonomy_id="curriculum", name="real",
        roots=tuple(unit_node(u) for u in taxonomy_data["curriculum"]),
    )
    question_types = Taxonomy(
        taxonomy_id="question_types", name="real qt",
        roots=tuple(
            TaxonomyNode(node_id=qt["id"], name=qt["name"], level=0)
            for qt in taxonomy_data["question_types"]
        ),
    )

    context = _context(tmp_path).for_document(REAL_PAPER_PATH)
    context.registry.register(curriculum, artifact_id="curriculum")
    context.registry.register(question_types, artifact_id="question_types")

    runner = PipelineRunner()
    runner.register(PaperImportStage()).register(RelationshipResolutionStage())
    runner.register(EducationalAnalysisStage()).register(CkoGenerationStage())
    summary = runner.run(context)

    assert summary.halted is False
    assert [r.status for r in summary.results] == [StageStatus.SUCCESS] * 4

    ckos = context.registry.all(CKO)
    paper = context.registry.all(PaperImport)[0]
    assert len(ckos) == len(paper.questions) == 49
    assert len({cko.cko_id for cko in ckos}) == 49

    by_qid = {q.identity.question_id: q for q in paper.questions}
    q37_cko_id = f"cko_{compute_checksum(by_qid['Q37'].content, by_qid['Q37'].options)}"
    q37_e_a_cko_id = f"cko_{compute_checksum(by_qid['Q37_e_A'].content, by_qid['Q37_e_A'].options)}"

    q37_cko = context.registry.get(CKO, q37_cko_id)
    assert q37_e_a_cko_id in q37_cko.relationships.child_cko_ids


def test_stage_reports_a_warning_when_ckos_merge_occurrences(tmp_path):
    # Build two tiny synthetic papers sharing one identical question, run them through
    # this stage's own execute(), and confirm the merge is surfaced as a warning.
    from tests.canonical_knowledge_object_generation.test_builder import _paper, _question, _register

    context = _context(tmp_path)
    _register(context, _paper("paper1", _question("Q1", stem="Same question")))
    _register(context, _paper("paper2", _question("Q9", stem="Same question")))

    result = CkoGenerationStage().execute(context)

    assert result.status is StageStatus.SUCCESS
    assert len(result.artifact_ids) == 1
    assert "1 CKO(s) merged" in result.warnings[0]
