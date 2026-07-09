from compiler_engine.domain.educational_analysis import BloomLevel, DifficultyLevel
from compiler_engine.educational_analysis.reference import CurriculumIndex, build_curriculum_index
from compiler_engine.educational_analysis.verification import build_educational_analysis, detect_issues
from compiler_engine.domain.taxonomy import Taxonomy, TaxonomyNode
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

_METADATA = PaperMetadata(
    board="CBSE",
    conducting_body="X",
    region="Y",
    examination="Z",
    academic_session="2025-26",
    class_name="XII",
    subject="COMPUTER SCIENCE",
    subject_code="083",
    duration="3 HOURS",
    maximum_marks=10,
    set="SET A",
    total_questions=1,
    total_sections=1,
)

_SECTIONS = (PaperSection(section_id="sec_a", title="SECTION A", marks_per_question=1, question_range="1-1"),)

_VALID_CURRICULUM = build_curriculum_index(
    Taxonomy(
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
)
_VALID_QUESTION_TYPES = frozenset({"qt_mcq"})
_EMPTY_CURRICULUM = CurriculumIndex()
_EMPTY_QUESTION_TYPES: frozenset[str] = frozenset()


def _classification(**overrides) -> RawClassification:
    fields = dict(
        chapter="ch_x",
        topic="top_x",
        concept="con_x",
        keywords=("kw1", "kw2"),
        difficulty="diff_easy",
        bloom_level="bloom_remember",
        question_type="qt_mcq",
    )
    fields.update(overrides)
    return RawClassification(**fields)


def _question(question_id: str, original_question_number: str = "1", **classification_overrides) -> RawQuestion:
    return RawQuestion(
        identity=RawQuestionIdentity(
            question_id=question_id,
            original_question_number=original_question_number,
            section_id="sec_a",
        ),
        classification=_classification(**classification_overrides),
        content=RawContent(blocks=(TextBlock(block_type="text", value="stem"),)),
        options=None,
        relationships=RawRelationships(),
        assessment=None,
    )


def _paper(*questions: RawQuestion) -> PaperImport:
    return PaperImport(
        schema_version="1.0",
        paper_id="test_paper",
        paper_metadata=_METADATA,
        sections=_SECTIONS,
        questions=questions,
    )


def test_clean_classification_has_no_issues():
    paper = _paper(_question("Q1"))
    issues = detect_issues(paper, _VALID_CURRICULUM, _VALID_QUESTION_TYPES)
    assert issues == ()


def test_unknown_chapter_is_flagged():
    paper = _paper(_question("Q1", chapter="ch_missing"))
    issues = detect_issues(paper, _VALID_CURRICULUM, _VALID_QUESTION_TYPES)
    # topic=top_x is valid and expects chapter=ch_x, so an unknown chapter here also
    # trips the topic/chapter hierarchy check -- both findings are genuine.
    assert any(i.code == "UNKNOWN_TAXONOMY_ID" and "chapter" in i.field_path for i in issues)
    assert any(i.code == "HIERARCHY_MISMATCH" for i in issues)


def test_unknown_topic_concept_and_question_type_are_all_flagged():
    paper = _paper(
        _question("Q1", topic="top_missing", concept="con_missing", question_type="qt_missing")
    )
    issues = detect_issues(paper, _VALID_CURRICULUM, _VALID_QUESTION_TYPES)
    codes = [i.code for i in issues]
    assert codes.count("UNKNOWN_TAXONOMY_ID") == 3


def test_invalid_bloom_level_is_flagged():
    paper = _paper(_question("Q1", bloom_level="bloom_nonsense"))
    issues = detect_issues(paper, _VALID_CURRICULUM, _VALID_QUESTION_TYPES)
    assert [i.code for i in issues] == ["INVALID_BLOOM_LEVEL"]


def test_invalid_difficulty_is_flagged():
    paper = _paper(_question("Q1", difficulty="diff_extreme"))
    issues = detect_issues(paper, _VALID_CURRICULUM, _VALID_QUESTION_TYPES)
    assert [i.code for i in issues] == ["INVALID_DIFFICULTY_TIER"]


def test_topic_under_wrong_chapter_is_a_hierarchy_mismatch():
    # top_x really belongs under ch_x in the reference curriculum; declare a different chapter
    paper = _paper(_question("Q1", chapter="ch_wrong", topic="top_x", concept="con_x"))
    issues = detect_issues(paper, _VALID_CURRICULUM, _VALID_QUESTION_TYPES)
    # chapter=ch_wrong is itself unknown, AND topic/chapter pairing disagrees with the
    # taxonomy -- both are genuine, independent findings.
    codes = [i.code for i in issues]
    assert "UNKNOWN_TAXONOMY_ID" in codes
    assert "HIERARCHY_MISMATCH" in codes


def test_concept_under_wrong_topic_is_a_hierarchy_mismatch():
    paper = _paper(_question("Q1", topic="top_wrong_but_unknown", concept="con_x"))
    issues = detect_issues(paper, _VALID_CURRICULUM, _VALID_QUESTION_TYPES)
    # concept=con_x exists and expects topic=top_x; declared topic disagrees.
    assert any(i.code == "HIERARCHY_MISMATCH" and "concept" in i.field_path for i in issues)


def test_hierarchy_is_not_checked_when_the_id_itself_is_unknown():
    # concept must also be unknown here, otherwise a *valid* concept's own expected-topic
    # check would independently (and correctly) fire a HIERARCHY_MISMATCH of its own.
    paper = _paper(_question("Q1", topic="top_missing", concept="con_missing"))
    issues = detect_issues(paper, _VALID_CURRICULUM, _VALID_QUESTION_TYPES)
    assert not any(i.code == "HIERARCHY_MISMATCH" for i in issues)


def test_empty_classification_field_is_missing_metadata():
    paper = _paper(_question("Q1", chapter=""))
    issues = detect_issues(paper, _EMPTY_CURRICULUM, _EMPTY_QUESTION_TYPES)
    assert any(i.code == "MISSING_EDUCATIONAL_METADATA" for i in issues)


def test_no_keywords_is_flagged_as_a_warning():
    paper = _paper(_question("Q1", keywords=()))
    issues = detect_issues(paper, _VALID_CURRICULUM, _VALID_QUESTION_TYPES)
    keyword_issues = [i for i in issues if i.code == "INVALID_KEYWORDS"]
    assert len(keyword_issues) == 1
    assert keyword_issues[0].severity.value == "warning"


def test_duplicate_keyword_is_flagged():
    paper = _paper(_question("Q1", keywords=("loop", "loop")))
    issues = detect_issues(paper, _VALID_CURRICULUM, _VALID_QUESTION_TYPES)
    assert any(i.code == "INVALID_KEYWORDS" and "duplicate" in i.message for i in issues)


def test_blank_keyword_is_flagged():
    paper = _paper(_question("Q1", keywords=("loop", "  ")))
    issues = detect_issues(paper, _VALID_CURRICULUM, _VALID_QUESTION_TYPES)
    assert any(i.code == "INVALID_KEYWORDS" and "blank" in i.message for i in issues)


def test_duplicate_concept_within_question_group_is_a_warning():
    a = _question("Q1_A", original_question_number="1", concept="con_x")
    b = _question("Q1_B", original_question_number="1", concept="con_x")
    paper = _paper(a, b)
    issues = detect_issues(paper, _VALID_CURRICULUM, _VALID_QUESTION_TYPES)
    dup_issues = [i for i in issues if i.code == "DUPLICATE_CONCEPT_IN_QUESTION_GROUP"]
    assert len(dup_issues) == 1
    assert dup_issues[0].severity.value == "warning"


def test_same_concept_across_different_question_groups_is_not_flagged():
    a = _question("Q1", original_question_number="1", concept="con_x")
    b = _question("Q2", original_question_number="2", concept="con_x")
    paper = _paper(a, b)
    issues = detect_issues(paper, _VALID_CURRICULUM, _VALID_QUESTION_TYPES)
    assert not any(i.code == "DUPLICATE_CONCEPT_IN_QUESTION_GROUP" for i in issues)


def test_build_educational_analysis_maps_fields_faithfully():
    paper = _paper(_question("Q1"))
    analyses = build_educational_analysis(paper)

    assert len(analyses) == 1
    analysis = analyses[0]
    assert analysis.question_id == "Q1"
    assert analysis.subject == "COMPUTER SCIENCE"
    assert analysis.topic == "top_x"
    assert analysis.subtopic == "con_x"
    assert analysis.taxonomy_path == ("ch_x", "top_x", "con_x")
    assert analysis.difficulty is DifficultyLevel.EASY
    assert analysis.bloom_level is BloomLevel.REMEMBER
    assert analysis.keywords == ("kw1", "kw2")


def test_build_educational_analysis_never_fails_on_bad_bloom_or_difficulty():
    paper = _paper(_question("Q1", bloom_level="garbage", difficulty="garbage"))
    analyses = build_educational_analysis(paper)

    assert len(analyses) == 1
    assert analyses[0].bloom_level is None
    assert analyses[0].difficulty is None


def test_build_educational_analysis_produces_one_object_per_question_regardless_of_validity():
    paper = _paper(_question("Q1", chapter="totally_unknown"))
    analyses = build_educational_analysis(paper)
    assert len(analyses) == 1
    assert analyses[0].taxonomy_path[0] == "totally_unknown"
