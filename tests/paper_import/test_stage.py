from pathlib import Path

import pytest

from compiler_engine.core.config import CompilerConfig
from compiler_engine.core.errors import CompilerImportError
from compiler_engine.domain.validation_report import ValidationReport
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.pipeline.stage import StageStatus
from compiler_engine.paper_import.schema import PaperImport, RawQuestion
from compiler_engine.paper_import.stage import PaperImportStage

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


def test_validate_inputs_requires_current_document(tmp_path):
    stage = PaperImportStage()
    with pytest.raises(CompilerImportError):
        stage.validate_inputs(_context(tmp_path))


def test_validate_inputs_requires_the_file_to_exist(tmp_path):
    stage = PaperImportStage()
    context = _context(tmp_path).for_document(tmp_path / "missing.json")
    with pytest.raises(CompilerImportError):
        stage.validate_inputs(context)


def test_execute_on_malformed_json_fails_the_stage(tmp_path):
    paper_path = tmp_path / "paper.json"
    paper_path.write_text("{not valid json", encoding="utf-8")
    context = _context(tmp_path).for_document(paper_path)

    result = PaperImportStage().execute(context)

    assert result.status is StageStatus.FAILED
    assert result.errors


def test_execute_on_a_clean_minimal_paper_succeeds_and_registers_artifacts(tmp_path):
    paper_path = tmp_path / "paper.json"
    paper_path.write_text(_MINIMAL_VALID_PAPER, encoding="utf-8")
    context = _context(tmp_path).for_document(paper_path)

    result = PaperImportStage().execute(context)

    assert result.status is StageStatus.SUCCESS
    assert result.warnings == ()
    assert len(result.artifact_ids) == 3  # paper + 1 question + validation report

    report = context.registry.get(ValidationReport, "minimal_paper")
    assert report.is_valid is True
    assert report.issues == ()

    assert context.registry.get(PaperImport, "minimal_paper").paper_id == "minimal_paper"
    assert context.registry.get(RawQuestion, "minimal_paper::Q1").identity.question_id == "Q1"


def test_execute_on_the_real_gold_standard_paper(tmp_path):
    context = _context(tmp_path).for_document(REAL_PAPER_PATH)

    result = PaperImportStage().execute(context)

    assert result.status is StageStatus.SUCCESS
    assert len(result.warnings) == 1
    assert "2 error(s)" in result.warnings[0]
    assert len(result.artifact_ids) == 1 + 49 + 1

    report = context.registry.get(ValidationReport, "cbse_2025_26_xii_083_set_a")
    assert report.is_valid is False
    assert [issue.code for issue in report.issues] == [
        "DANGLING_RELATIONSHIP_REFERENCE",
        "DANGLING_RELATIONSHIP_REFERENCE",
    ]
    assert {issue.message.split("'")[1] for issue in report.issues} == {"Q23_i", "Q23_ii"}
