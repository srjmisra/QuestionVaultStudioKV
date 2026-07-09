from compiler_engine.paper_import.schema import (
    PaperImport,
    PaperMetadata,
    PaperSection,
    RawClassification,
    RawContent,
    RawQuestion,
    RawQuestionIdentity,
    RawRelationships,
    TextBlock,
)
from compiler_engine.paper_import.validation import validate_paper

_METADATA = PaperMetadata(
    board="CBSE",
    conducting_body="X",
    region="Y",
    examination="Z",
    academic_session="2025-26",
    class_name="XII",
    subject="CS",
    subject_code="083",
    duration="3 HOURS",
    maximum_marks=10,
    set="SET A",
    total_questions=1,
    total_sections=1,
)

_SECTIONS = (PaperSection(section_id="sec_a", title="SECTION A", marks_per_question=1, question_range="1-1"),)


def _classification() -> RawClassification:
    return RawClassification(
        chapter="ch_x",
        topic="top_x",
        concept="con_x",
        keywords=("kw",),
        difficulty="diff_easy",
        bloom_level="bloom_remember",
        question_type="qt_mcq",
    )


def _question(
    question_id: str,
    *,
    section_id: str = "sec_a",
    parent_id: str | None = None,
    child_ids: tuple[str, ...] = (),
    sibling_or_ids: tuple[str, ...] = (),
) -> RawQuestion:
    return RawQuestion(
        identity=RawQuestionIdentity(
            question_id=question_id, original_question_number="1", section_id=section_id
        ),
        classification=_classification(),
        content=RawContent(blocks=(TextBlock(block_type="text", value="stem"),)),
        options=None,
        relationships=RawRelationships(
            parent_id=parent_id, child_ids=child_ids, sibling_or_ids=sibling_or_ids
        ),
        assessment=None,
    )


def _paper(*, schema_version: str = "1.0", questions: tuple[RawQuestion, ...]) -> PaperImport:
    return PaperImport(
        schema_version=schema_version,
        paper_id="test_paper",
        paper_metadata=_METADATA,
        sections=_SECTIONS,
        questions=questions,
    )


def test_clean_paper_has_no_issues():
    paper = _paper(questions=(_question("Q1"),))
    assert validate_paper(paper) == ()


def test_unsupported_schema_version_is_flagged():
    paper = _paper(schema_version="2.0", questions=(_question("Q1"),))
    issues = validate_paper(paper)
    assert [i.code for i in issues] == ["UNSUPPORTED_SCHEMA_VERSION"]


def test_duplicate_question_id_is_flagged():
    paper = _paper(questions=(_question("Q1"), _question("Q1")))
    issues = validate_paper(paper)
    assert [i.code for i in issues] == ["DUPLICATE_QUESTION_ID"]
    assert issues[0].field_path == "questions[1].identity.question_id"


def test_unknown_section_reference_is_flagged():
    paper = _paper(questions=(_question("Q1", section_id="sec_missing"),))
    issues = validate_paper(paper)
    assert [i.code for i in issues] == ["UNKNOWN_SECTION_REFERENCE"]


def test_dangling_parent_id_is_flagged():
    paper = _paper(questions=(_question("Q1", parent_id="Q_missing"),))
    issues = validate_paper(paper)
    assert [i.code for i in issues] == ["DANGLING_RELATIONSHIP_REFERENCE"]
    assert "parent_id" in issues[0].field_path


def test_dangling_child_id_is_flagged():
    paper = _paper(questions=(_question("Q1", child_ids=("Q_missing",)),))
    issues = validate_paper(paper)
    assert [i.code for i in issues] == ["DANGLING_RELATIONSHIP_REFERENCE"]


def test_dangling_sibling_or_id_is_flagged():
    paper = _paper(questions=(_question("Q1", sibling_or_ids=("Q_missing",)),))
    issues = validate_paper(paper)
    assert [i.code for i in issues] == ["DANGLING_RELATIONSHIP_REFERENCE"]


def test_valid_parent_child_relationship_is_not_flagged():
    parent = _question("Q1", child_ids=("Q1_a",))
    child = _question("Q1_a", parent_id="Q1")
    paper = _paper(questions=(parent, child))
    assert validate_paper(paper) == ()


def test_multiple_issues_are_all_reported():
    paper = _paper(
        schema_version="2.0",
        questions=(_question("Q1"), _question("Q1"), _question("Q2", parent_id="Q_missing")),
    )
    issues = validate_paper(paper)
    codes = [i.code for i in issues]
    assert "UNSUPPORTED_SCHEMA_VERSION" in codes
    assert "DUPLICATE_QUESTION_ID" in codes
    assert "DANGLING_RELATIONSHIP_REFERENCE" in codes
