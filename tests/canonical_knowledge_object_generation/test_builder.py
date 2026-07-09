from compiler_engine.canonical_knowledge_object_generation.builder import generate_ckos
from compiler_engine.core.config import CompilerConfig
from compiler_engine.domain.educational_analysis import EducationalAnalysis
from compiler_engine.domain.relationship_graph import (
    RelationshipEdge,
    RelationshipGraph,
    RelationshipNode,
    RelationshipType,
)
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
from compiler_engine.pipeline.context import CompilerContext


def _metadata(**overrides) -> PaperMetadata:
    fields = dict(
        board="CBSE",
        conducting_body="X",
        region="Delhi",
        examination="Board Exam",
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
    fields.update(overrides)
    return PaperMetadata(**fields)


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
    stem: str = "What is 2+2?",
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
        content=RawContent(blocks=(TextBlock(block_type="text", value=stem),)),
        options=None,
        relationships=RawRelationships(
            parent_id=parent_id, child_ids=child_ids, sibling_or_ids=sibling_or_ids
        ),
        assessment=None,
    )


def _paper(paper_id: str, *questions: RawQuestion, **metadata_overrides) -> PaperImport:
    return PaperImport(
        schema_version="1.0",
        paper_id=paper_id,
        paper_metadata=_metadata(**metadata_overrides),
        sections=(PaperSection(section_id="sec_a", title="A", marks_per_question=2, question_range="1-1"),),
        questions=questions,
    )


def _graph_for(paper: PaperImport) -> RelationshipGraph:
    """Builds a trivial RelationshipGraph mirroring each question's own declared
    relationships -- enough for these tests without depending on Sprint 4 code."""
    nodes = []
    edges = []
    or_groups: dict[str, str] = {}
    for question in paper.questions:
        rel = question.relationships
        if rel.sibling_or_ids:
            members = tuple(sorted((question.identity.question_id, *rel.sibling_or_ids)))
            group_id = "|".join(members)
            or_groups[question.identity.question_id] = group_id
        for child_id in rel.child_ids:
            edges.append(
                RelationshipEdge(
                    from_id=question.identity.question_id,
                    to_id=child_id,
                    relationship_type=RelationshipType.PARENT_CHILD,
                )
            )
    for question in paper.questions:
        nodes.append(
            RelationshipNode(
                question_id=question.identity.question_id,
                is_resolved=True,
                parent_id=question.relationships.parent_id,
                child_ids=question.relationships.child_ids,
                or_choice_group_id=or_groups.get(question.identity.question_id),
            )
        )
    return RelationshipGraph(paper_id=paper.paper_id, nodes=tuple(nodes), edges=tuple(edges))


def _context() -> CompilerContext:
    config = CompilerConfig(import_workspace="/tmp/x", assets_folder="/tmp/y", output_folder="/tmp/z")
    return CompilerContext.create(config)


def _register(context: CompilerContext, paper: PaperImport) -> None:
    context.registry.register(paper, artifact_id=paper.paper_id)
    context.registry.register(_graph_for(paper), artifact_id=paper.paper_id)
    for question in paper.questions:
        context.registry.register(
            EducationalAnalysis(
                question_id=question.identity.question_id,
                subject=paper.paper_metadata.subject,
                topic=question.classification.topic,
                subtopic=question.classification.concept,
            ),
            artifact_id=f"{paper.paper_id}::{question.identity.question_id}",
        )


def test_single_question_produces_one_cko_with_one_occurrence():
    paper = _paper("paper1", _question("Q1"))
    context = _context()
    _register(context, paper)

    ckos = generate_ckos(context)

    assert len(ckos) == 1
    cko = ckos[0]
    assert cko.version == 1
    assert len(cko.lineage.occurrences) == 1
    occurrence = cko.lineage.occurrences[0]
    assert occurrence.paper_id == "paper1"
    assert occurrence.allocated_marks == 2


def test_cko_id_is_deterministic_and_content_derived():
    paper = _paper("paper1", _question("Q1"))
    context = _context()
    _register(context, paper)
    ckos = generate_ckos(context)

    # Regenerating from the same registry contents must produce the identical cko_id.
    ckos_again = generate_ckos(context)
    assert ckos[0].cko_id == ckos_again[0].cko_id
    assert ckos[0].checksum == ckos_again[0].checksum


def test_identical_question_from_two_different_papers_merges_into_one_cko():
    paper1 = _paper("paper1", _question("Q1", stem="What is 2+2?"))
    paper2 = _paper(
        "paper2",
        _question("Q5", stem="What is 2+2?"),
        examination="Different Exam",
        academic_session="2026-27",
    )
    context = _context()
    _register(context, paper1)
    _register(context, paper2)

    ckos = generate_ckos(context)

    assert len(ckos) == 1
    cko = ckos[0]
    # Version tracks editorial evolution, not occurrence count -- two occurrences of
    # the identical, unedited question must NOT bump version.
    assert cko.version == 1
    assert len(cko.lineage.occurrences) == 2
    assert {o.paper_id for o in cko.lineage.occurrences} == {"paper1", "paper2"}


def test_three_occurrences_of_the_same_question_still_leave_version_at_one():
    # Mirrors the Sprint 6 review example directly: a question appearing in 2024, 2025,
    # and 2026 boards has occurrences = 3, but version must remain 1 -- only editorial
    # changes to canonical content should ever bump it, and this stage never edits.
    papers = [
        _paper(f"paper_{year}", _question("Q1", stem="What is 2+2?"), academic_session=f"{year}-{year + 1}")
        for year in (2024, 2025, 2026)
    ]
    context = _context()
    for paper in papers:
        _register(context, paper)

    ckos = generate_ckos(context)

    assert len(ckos) == 1
    assert ckos[0].version == 1
    assert len(ckos[0].lineage.occurrences) == 3


def test_different_questions_from_two_papers_produce_two_ckos():
    paper1 = _paper("paper1", _question("Q1", stem="What is 2+2?"))
    paper2 = _paper("paper2", _question("Q1", stem="What is 3+3?"))
    context = _context()
    _register(context, paper1)
    _register(context, paper2)

    ckos = generate_ckos(context)

    assert len(ckos) == 2
    assert ckos[0].cko_id != ckos[1].cko_id


def test_parent_child_relationships_resolve_to_cko_ids():
    parent = _question("Q1", stem="Parent", child_ids=("Q1_a",))
    child = _question("Q1_a", stem="Child", parent_id="Q1")
    paper = _paper("paper1", parent, child)
    context = _context()
    _register(context, paper)

    ckos = {cko.classification.question_id: cko for cko in generate_ckos(context)}

    parent_cko = ckos["Q1"]
    child_cko = ckos["Q1_a"]
    assert child_cko.relationships.parent_cko_id == parent_cko.cko_id
    assert child_cko.cko_id in parent_cko.relationships.child_cko_ids


def test_or_choice_relationships_resolve_to_sibling_cko_ids():
    a = _question("Q1_A", stem="Option A", sibling_or_ids=("Q1_B",))
    b = _question("Q1_B", stem="Option B", sibling_or_ids=("Q1_A",))
    paper = _paper("paper1", a, b)
    context = _context()
    _register(context, paper)

    ckos = {cko.classification.question_id: cko for cko in generate_ckos(context)}

    assert ckos["Q1_A"].relationships.sibling_or_cko_ids == (ckos["Q1_B"].cko_id,)
    assert ckos["Q1_B"].relationships.sibling_or_cko_ids == (ckos["Q1_A"].cko_id,)


def test_dangling_parent_reference_leaves_parent_cko_id_none_without_crashing():
    orphan_child = _question("Q1_a", stem="Child", parent_id="Q_ghost")
    paper = _paper("paper1", orphan_child)
    context = _context()
    _register(context, paper)

    ckos = generate_ckos(context)

    assert len(ckos) == 1
    assert ckos[0].relationships.parent_cko_id is None


def test_allocated_marks_is_none_when_section_does_not_resolve():
    question = _question("Q1", section_id="sec_missing")
    paper = _paper("paper1", question)
    context = _context()
    _register(context, paper)

    ckos = generate_ckos(context)

    assert ckos[0].lineage.occurrences[0].allocated_marks is None


def test_classification_is_preserved_from_educational_analysis():
    paper = _paper("paper1", _question("Q1"))
    context = _context()
    _register(context, paper)

    cko = generate_ckos(context)[0]

    assert cko.classification.subject == "COMPUTER SCIENCE"
    assert cko.classification.topic == "top_x"
    assert cko.classification.subtopic == "con_x"


def test_content_and_options_are_preserved_exactly():
    question = _question("Q1", stem="Exact wording, not to be touched.")
    paper = _paper("paper1", question)
    context = _context()
    _register(context, paper)

    cko = generate_ckos(context)[0]

    assert cko.content == question.content
    assert cko.options == question.options
