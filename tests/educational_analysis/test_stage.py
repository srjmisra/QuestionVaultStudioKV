from pathlib import Path

import pytest

from compiler_engine.core.config import CompilerConfig
from compiler_engine.core.errors import CompilerError
from compiler_engine.domain.educational_analysis import EducationalAnalysis
from compiler_engine.domain.taxonomy import Taxonomy, TaxonomyNode
from compiler_engine.domain.validation_report import ValidationReport
from compiler_engine.educational_analysis.stage import EducationalAnalysisStage
from compiler_engine.paper_import.stage import PaperImportStage
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.pipeline.runner import PipelineRunner

REAL_PAPER_PATH = Path(__file__).resolve().parents[2] / "imports" / "paper.json"

_MINIMAL_VALID_PAPER = """
{
  "schema_version": "1.0",
  "paper_id": "minimal_paper",
  "paper_metadata": {
    "board": "CBSE", "conducting_body": "X", "region": "Y", "examination": "Z",
    "academic_session": "2025-26", "class": "XII", "subject": "COMPUTER SCIENCE",
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


def _register_valid_curriculum(context: CompilerContext) -> None:
    curriculum = Taxonomy(
        taxonomy_id="curriculum",
        name="test",
        roots=(
            TaxonomyNode(
                node_id="unit_1",
                name="Unit 1",
                level=0,
                children=(
                    TaxonomyNode(
                        node_id="ch_x",
                        name="Chapter X",
                        level=1,
                        children=(
                            TaxonomyNode(
                                node_id="top_x",
                                name="Topic X",
                                level=2,
                                children=(TaxonomyNode(node_id="con_x", name="Concept X", level=3),),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    question_types = Taxonomy(
        taxonomy_id="question_types",
        name="question types",
        roots=(TaxonomyNode(node_id="qt_mcq", name="MCQ", level=0),),
    )
    context.registry.register(curriculum, artifact_id="curriculum")
    context.registry.register(question_types, artifact_id="question_types")


def test_validate_inputs_requires_a_registered_paper_import(tmp_path):
    context = _context(tmp_path)
    _register_valid_curriculum(context)
    with pytest.raises(CompilerError):
        EducationalAnalysisStage().validate_inputs(context)


def test_validate_inputs_requires_the_curriculum_taxonomy(tmp_path):
    paper_path = tmp_path / "paper.json"
    paper_path.write_text(_MINIMAL_VALID_PAPER, encoding="utf-8")
    context = _context(tmp_path).for_document(paper_path)
    PaperImportStage().execute(context)

    with pytest.raises(CompilerError):
        EducationalAnalysisStage().validate_inputs(context)


def test_execute_on_a_clean_minimal_paper_succeeds(tmp_path):
    paper_path = tmp_path / "paper.json"
    paper_path.write_text(_MINIMAL_VALID_PAPER, encoding="utf-8")
    context = _context(tmp_path).for_document(paper_path)
    _register_valid_curriculum(context)

    PaperImportStage().execute(context)
    result = EducationalAnalysisStage().execute(context)

    assert result.warnings == ()
    assert len(result.artifact_ids) == 2  # 1 EducationalAnalysis + 1 report

    report = context.registry.get(ValidationReport, "minimal_paper::educational_analysis")
    assert report.is_valid is True
    assert report.issues == ()

    analysis = context.registry.get(EducationalAnalysis, "minimal_paper::Q1")
    assert analysis.subject == "COMPUTER SCIENCE"
    assert analysis.taxonomy_path == ("ch_x", "top_x", "con_x")


def test_full_pipeline_on_the_real_paper_with_a_placeholder_taxonomy(tmp_path):
    # No real "QuestionVault Taxonomy v1.0" exists yet -- this deliberately empty
    # taxonomy proves the stage reports everything as unverifiable rather than
    # inventing a taxonomy that would make the real paper look clean.
    context = _context(tmp_path).for_document(REAL_PAPER_PATH)
    context.registry.register(
        Taxonomy(taxonomy_id="curriculum", name="placeholder", roots=()), artifact_id="curriculum"
    )
    context.registry.register(
        Taxonomy(taxonomy_id="question_types", name="placeholder", roots=()),
        artifact_id="question_types",
    )

    runner = PipelineRunner()
    runner.register(PaperImportStage()).register(EducationalAnalysisStage())
    summary = runner.run(context)

    assert summary.halted is False

    report = context.registry.get(
        ValidationReport, "cbse_2025_26_xii_083_set_a::educational_analysis"
    )
    assert report.is_valid is False
    # 49 questions x 4 taxonomy-dependent fields (chapter/topic/concept/question_type)
    unknown_id_issues = [i for i in report.issues if i.code == "UNKNOWN_TAXONOMY_ID"]
    assert len(unknown_id_issues) == 49 * 4

    # Bloom/difficulty already map onto Sprint 1's fixed enums and need no external
    # taxonomy, so the real paper's values should all still be recognized.
    assert not any(i.code == "INVALID_BLOOM_LEVEL" for i in report.issues)
    assert not any(i.code == "INVALID_DIFFICULTY_TIER" for i in report.issues)

    assert len(context.registry.all(EducationalAnalysis)) == 49
