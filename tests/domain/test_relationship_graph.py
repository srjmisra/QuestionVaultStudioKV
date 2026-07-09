import pytest

from compiler_engine.core.errors import SchemaError
from compiler_engine.domain.relationship_graph import (
    RelationshipEdge,
    RelationshipGraph,
    RelationshipNode,
    RelationshipType,
)


def _sample_graph() -> RelationshipGraph:
    parent = RelationshipNode(question_id="Q1", is_resolved=True, child_ids=("Q1_a",))
    child = RelationshipNode(question_id="Q1_a", is_resolved=True, parent_id="Q1")
    orphan = RelationshipNode(question_id="Q_ghost", is_resolved=False)
    edge = RelationshipEdge(from_id="Q1", to_id="Q1_a", relationship_type=RelationshipType.PARENT_CHILD)
    return RelationshipGraph(paper_id="paper1", nodes=(parent, child, orphan), edges=(edge,))


def test_builds_a_graph_with_resolved_and_orphan_nodes():
    graph = _sample_graph()
    assert graph.nodes[0].child_ids == ("Q1_a",)
    assert graph.nodes[2].is_resolved is False


def test_round_trips_through_json():
    graph = _sample_graph()
    assert RelationshipGraph.from_json(graph.to_json()) == graph


def test_rejects_unknown_relationship_type():
    with pytest.raises(SchemaError):
        RelationshipEdge.from_dict({"from_id": "a", "to_id": "b", "relationship_type": "cousin"})


def test_nodes_and_edges_are_frozen():
    graph = _sample_graph()
    with pytest.raises(Exception):
        graph.nodes = ()
