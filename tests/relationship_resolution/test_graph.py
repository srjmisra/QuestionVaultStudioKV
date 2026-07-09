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
from compiler_engine.relationship_resolution.graph import build_graph, detect_issues

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
    parent_id: str | None = None,
    child_ids: tuple[str, ...] = (),
    sibling_or_ids: tuple[str, ...] = (),
) -> RawQuestion:
    return RawQuestion(
        identity=RawQuestionIdentity(
            question_id=question_id, original_question_number="1", section_id="sec_a"
        ),
        classification=_classification(),
        content=RawContent(blocks=(TextBlock(block_type="text", value="stem"),)),
        options=None,
        relationships=RawRelationships(
            parent_id=parent_id, child_ids=child_ids, sibling_or_ids=sibling_or_ids
        ),
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


def test_standalone_questions_produce_no_edges_and_no_issues():
    paper = _paper(_question("Q1"), _question("Q2"))
    graph = build_graph(paper)

    assert graph.edges == ()
    assert {n.question_id for n in graph.nodes} == {"Q1", "Q2"}
    assert all(n.is_resolved for n in graph.nodes)
    assert detect_issues(paper, graph) == ()


def test_consistent_parent_child_produces_one_edge_and_no_issues():
    parent = _question("Q1", child_ids=("Q1_a",))
    child = _question("Q1_a", parent_id="Q1")
    paper = _paper(parent, child)
    graph = build_graph(paper)

    assert len(graph.edges) == 1
    assert graph.edges[0].from_id == "Q1"
    assert graph.edges[0].to_id == "Q1_a"
    assert detect_issues(paper, graph) == ()


def test_consistent_or_choice_produces_one_grouped_edge_and_no_issues():
    a = _question("Q1_A", sibling_or_ids=("Q1_B",))
    b = _question("Q1_B", sibling_or_ids=("Q1_A",))
    paper = _paper(a, b)
    graph = build_graph(paper)

    assert len(graph.edges) == 1
    node_a = next(n for n in graph.nodes if n.question_id == "Q1_A")
    node_b = next(n for n in graph.nodes if n.question_id == "Q1_B")
    assert node_a.or_choice_group_id == node_b.or_choice_group_id
    assert node_a.or_choice_group_id == "Q1_A|Q1_B"
    assert detect_issues(paper, graph) == ()


def test_or_choice_group_of_three_shares_one_group_id():
    a = _question("Q1_A", sibling_or_ids=("Q1_B", "Q1_C"))
    b = _question("Q1_B", sibling_or_ids=("Q1_A", "Q1_C"))
    c = _question("Q1_C", sibling_or_ids=("Q1_A", "Q1_B"))
    paper = _paper(a, b, c)
    graph = build_graph(paper)

    group_ids = {n.or_choice_group_id for n in graph.nodes}
    assert group_ids == {"Q1_A|Q1_B|Q1_C"}


def test_dangling_parent_reference_is_an_orphan_node_and_issue():
    child = _question("Q1_a", parent_id="Q_ghost")
    paper = _paper(child)
    graph = build_graph(paper)

    orphan = next(n for n in graph.nodes if n.question_id == "Q_ghost")
    assert orphan.is_resolved is False

    issues = detect_issues(paper, graph)
    assert [i.code for i in issues] == ["ORPHAN_REFERENCE"]


def test_one_sided_parent_declaration_is_flagged():
    # child claims a parent that exists, but the parent does not list the child back
    parent = _question("Q1")
    child = _question("Q1_a", parent_id="Q1")
    paper = _paper(parent, child)
    issues = detect_issues(paper, build_graph(paper))

    assert [i.code for i in issues] == ["BIDIRECTIONAL_PARENT_CHILD_MISMATCH"]


def test_one_sided_child_declaration_is_flagged():
    # parent claims a child that exists, but the child does not point back
    parent = _question("Q1", child_ids=("Q1_a",))
    child = _question("Q1_a")
    paper = _paper(parent, child)
    issues = detect_issues(paper, build_graph(paper))

    assert [i.code for i in issues] == ["BIDIRECTIONAL_PARENT_CHILD_MISMATCH"]


def test_conflicting_parent_claims_are_flagged():
    real_parent = _question("Q2", child_ids=("Q1_a",))
    claimed_parent = _question("Q1")
    child = _question("Q1_a", parent_id="Q1")
    paper = _paper(real_parent, claimed_parent, child)
    issues = detect_issues(paper, build_graph(paper))

    codes = [i.code for i in issues]
    assert codes.count("BIDIRECTIONAL_PARENT_CHILD_MISMATCH") == 2


def test_one_sided_or_choice_is_flagged():
    a = _question("Q1_A", sibling_or_ids=("Q1_B",))
    b = _question("Q1_B")
    paper = _paper(a, b)
    issues = detect_issues(paper, build_graph(paper))

    assert [i.code for i in issues] == ["BIDIRECTIONAL_OR_CHOICE_MISMATCH"]


def test_two_node_cycle_is_detected():
    a = _question("Q1", parent_id="Q2", child_ids=("Q2",))
    b = _question("Q2", parent_id="Q1", child_ids=("Q1",))
    paper = _paper(a, b)
    issues = detect_issues(paper, build_graph(paper))

    circular = [i for i in issues if i.code == "CIRCULAR_REFERENCE"]
    assert len(circular) == 1


def test_self_referencing_parent_is_a_cycle():
    a = _question("Q1", parent_id="Q1", child_ids=("Q1",))
    paper = _paper(a)
    issues = detect_issues(paper, build_graph(paper))

    assert any(i.code == "CIRCULAR_REFERENCE" for i in issues)


def test_or_choice_pairs_are_never_reported_as_cycles():
    a = _question("Q1_A", sibling_or_ids=("Q1_B",))
    b = _question("Q1_B", sibling_or_ids=("Q1_A",))
    paper = _paper(a, b)
    issues = detect_issues(paper, build_graph(paper))

    assert not any(i.code == "CIRCULAR_REFERENCE" for i in issues)
