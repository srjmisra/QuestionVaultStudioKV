from pathlib import Path

import pytest

from compiler_engine.core.config import CompilerConfig
from compiler_engine.core.errors import CompilerError
from compiler_engine.domain.relationship_graph import RelationshipGraph
from compiler_engine.domain.validation_report import ValidationReport
from compiler_engine.paper_import.stage import PaperImportStage
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.pipeline.runner import PipelineRunner
from compiler_engine.pipeline.stage import StageStatus
from compiler_engine.relationship_resolution.stage import RelationshipResolutionStage

REAL_PAPER_PATH = Path(__file__).resolve().parents[2] / "imports" / "paper.json"

_MINIMAL_VALID_PAPER = """
{
  "schema_version": "1.0",
  "paper_id": "minimal_paper",
  "paper_metadata": {
    "board": "CBSE", "conducting_body": "X", "region": "Y", "examination": "Z",
    "academic_session": "2025-26", "class": "XII", "subject": "CS",
    "subject_code": "083", "duration": "3 HOURS", "maximum_marks": 1,
    "set": "SET A", "total_questions": 1, "total_sections": 1
  },
  "sections": [
    {"section_id": "sec_a", "title": "SECTION A", "marks_per_question": 1, "question_range": "1-1"}
  ],
  "questions": [
    {
      "identity": {"question_id": "Q1", "original_question_number": "1", "section_id": "sec_a"},
      "classification": {
        "chapter": "ch_x", "topic": "top_x", "concept": "con_x", "keywords": ["kw"],
        "difficulty": "diff_easy", "bloom_level": "bloom_remember", "question_type": "qt_mcq"
      },
      "content": {"blocks": [{"block_type": "text", "value": "stem"}]},
      "options": null,
      "relationships": {"parent_id": null, "child_ids": [], "sibling_or_ids": []},
      "assessment": null
    }
  ]
}
"""


def _context(tmp_path) -> CompilerContext:
    config = CompilerConfig(
        import_workspace=tmp_path / "import",
        assets_folder=tmp_path / "assets",
        output_folder=tmp_path / "output",
    )
    return CompilerContext.create(config)


def test_validate_inputs_requires_a_registered_paper_import(tmp_path):
    stage = RelationshipResolutionStage()
    with pytest.raises(CompilerError):
        stage.validate_inputs(_context(tmp_path))


def test_execute_on_a_clean_minimal_paper_succeeds(tmp_path):
    paper_path = tmp_path / "paper.json"
    paper_path.write_text(_MINIMAL_VALID_PAPER, encoding="utf-8")
    context = _context(tmp_path).for_document(paper_path)

    PaperImportStage().execute(context)
    result = RelationshipResolutionStage().execute(context)

    assert result.status is StageStatus.SUCCESS
    assert result.warnings == ()
    assert len(result.artifact_ids) == 2  # graph + relationship report

    report = context.registry.get(ValidationReport, "minimal_paper::relationships")
    assert report.is_valid is True
    assert report.issues == ()

    graph = context.registry.get(RelationshipGraph, "minimal_paper")
    assert len(graph.nodes) == 1
    assert graph.edges == ()


def test_full_pipeline_on_the_real_gold_standard_paper(tmp_path):
    context = _context(tmp_path).for_document(REAL_PAPER_PATH)

    runner = PipelineRunner()
    runner.register(PaperImportStage()).register(RelationshipResolutionStage())
    summary = runner.run(context)

    assert summary.halted is False
    assert [r.stage_name for r in summary.results] == ["paper_import", "relationship_resolution"]

    report = context.registry.get(ValidationReport, "cbse_2025_26_xii_083_set_a::relationships")
    assert report.is_valid is False
    assert [issue.code for issue in report.issues] == ["ORPHAN_REFERENCE"]
    assert "Q23" in report.issues[0].message

    graph = context.registry.get(RelationshipGraph, "cbse_2025_26_xii_083_set_a")
    assert len(graph.nodes) == 50  # 49 real questions + the Q23 orphan reference
    or_choice_groups = {n.or_choice_group_id for n in graph.nodes if n.or_choice_group_id}
    assert len(or_choice_groups) == 9
