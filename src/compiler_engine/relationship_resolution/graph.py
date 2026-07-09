"""Builds a RelationshipGraph from a PaperImport's per-question relationships, and
validates it: orphan references, bidirectional (parent/child and OR-choice) consistency,
and circular parent-child references.

`build_graph` transcribes declared relationships faithfully — a node's parent_id/child_ids
are always that question's own declaration, never inferred from another question's claim
about it. `detect_issues` is the only place cross-question agreement is checked.
"""

from __future__ import annotations

from collections import defaultdict

from compiler_engine.domain.relationship_graph import (
    RelationshipEdge,
    RelationshipGraph,
    RelationshipNode,
    RelationshipType,
)
from compiler_engine.domain.validation_report import ValidationIssue, ValidationSeverity
from compiler_engine.paper_import.schema import PaperImport


def build_graph(paper: PaperImport) -> RelationshipGraph:
    questions_by_id = {question.identity.question_id: question for question in paper.questions}
    known_ids = set(questions_by_id)

    parent_child_pairs: set[tuple[str, str]] = set()
    or_choice_pairs: set[tuple[str, str]] = set()
    referenced_ids: set[str] = set()

    for question in paper.questions:
        question_id = question.identity.question_id
        relationships = question.relationships

        if relationships.parent_id is not None:
            referenced_ids.add(relationships.parent_id)
            parent_child_pairs.add((relationships.parent_id, question_id))

        for child_id in relationships.child_ids:
            referenced_ids.add(child_id)
            parent_child_pairs.add((question_id, child_id))

        for sibling_id in relationships.sibling_or_ids:
            referenced_ids.add(sibling_id)
            or_choice_pairs.add(tuple(sorted((question_id, sibling_id))))

    or_choice_group_id_by_question = _group_or_choice_pairs(or_choice_pairs)

    all_node_ids = known_ids | referenced_ids
    nodes = []
    for question_id in sorted(all_node_ids):
        question = questions_by_id.get(question_id)
        nodes.append(
            RelationshipNode(
                question_id=question_id,
                is_resolved=question is not None,
                parent_id=question.relationships.parent_id if question else None,
                child_ids=question.relationships.child_ids if question else (),
                or_choice_group_id=or_choice_group_id_by_question.get(question_id),
            )
        )

    edges = [
        RelationshipEdge(from_id=parent_id, to_id=child_id, relationship_type=RelationshipType.PARENT_CHILD)
        for parent_id, child_id in sorted(parent_child_pairs)
    ] + [
        RelationshipEdge(from_id=left_id, to_id=right_id, relationship_type=RelationshipType.OR_CHOICE)
        for left_id, right_id in sorted(or_choice_pairs)
    ]

    return RelationshipGraph(paper_id=paper.paper_id, nodes=tuple(nodes), edges=tuple(edges))


def _group_or_choice_pairs(pairs: set[tuple[str, str]]) -> dict[str, str]:
    """Connected-components grouping: every question reachable from another via
    sibling_or_ids gets the same, deterministic group id (its members, sorted and joined).
    """
    adjacency: dict[str, set[str]] = defaultdict(set)
    for left_id, right_id in pairs:
        adjacency[left_id].add(right_id)
        adjacency[right_id].add(left_id)

    group_id_by_question: dict[str, str] = {}
    visited: set[str] = set()
    for start_id in sorted(adjacency):
        if start_id in visited:
            continue
        component: set[str] = set()
        stack = [start_id]
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(adjacency[current] - component)
        visited |= component
        group_id = "|".join(sorted(component))
        for question_id in component:
            group_id_by_question[question_id] = group_id

    return group_id_by_question


def detect_issues(paper: PaperImport, graph: RelationshipGraph) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    issues.extend(_check_orphan_references(graph))
    issues.extend(_check_bidirectional_parent_child(paper))
    issues.extend(_check_bidirectional_or_choice(paper))
    issues.extend(_check_circular_references(graph))
    return tuple(issues)


def _check_orphan_references(graph: RelationshipGraph) -> list[ValidationIssue]:
    return [
        ValidationIssue(
            code="ORPHAN_REFERENCE",
            message=(
                f"question_id {node.question_id!r} is referenced by a relationship but "
                "does not correspond to any question in this paper"
            ),
            severity=ValidationSeverity.ERROR,
            field_path=f"relationships.{node.question_id}",
        )
        for node in graph.nodes
        if not node.is_resolved
    ]


def _check_bidirectional_parent_child(paper: PaperImport) -> list[ValidationIssue]:
    questions_by_id = {question.identity.question_id: question for question in paper.questions}
    issues: list[ValidationIssue] = []

    for question in paper.questions:
        question_id = question.identity.question_id
        parent_id = question.relationships.parent_id

        if parent_id is not None and parent_id in questions_by_id:
            parent = questions_by_id[parent_id]
            if question_id not in parent.relationships.child_ids:
                issues.append(
                    ValidationIssue(
                        code="BIDIRECTIONAL_PARENT_CHILD_MISMATCH",
                        message=(
                            f"question {question_id!r} declares parent_id={parent_id!r}, but "
                            f"{parent_id!r}.relationships.child_ids does not include {question_id!r}"
                        ),
                        severity=ValidationSeverity.ERROR,
                        field_path=f"questions[{question_id}].relationships.parent_id",
                    )
                )

        for child_id in question.relationships.child_ids:
            child = questions_by_id.get(child_id)
            if child is not None and child.relationships.parent_id != question_id:
                issues.append(
                    ValidationIssue(
                        code="BIDIRECTIONAL_PARENT_CHILD_MISMATCH",
                        message=(
                            f"question {question_id!r} declares child_ids including "
                            f"{child_id!r}, but {child_id!r}.relationships.parent_id is "
                            f"{child.relationships.parent_id!r}, not {question_id!r}"
                        ),
                        severity=ValidationSeverity.ERROR,
                        field_path=f"questions[{question_id}].relationships.child_ids",
                    )
                )

    return issues


def _check_bidirectional_or_choice(paper: PaperImport) -> list[ValidationIssue]:
    questions_by_id = {question.identity.question_id: question for question in paper.questions}
    issues: list[ValidationIssue] = []

    for question in paper.questions:
        question_id = question.identity.question_id
        for sibling_id in question.relationships.sibling_or_ids:
            sibling = questions_by_id.get(sibling_id)
            if sibling is not None and question_id not in sibling.relationships.sibling_or_ids:
                issues.append(
                    ValidationIssue(
                        code="BIDIRECTIONAL_OR_CHOICE_MISMATCH",
                        message=(
                            f"question {question_id!r} declares {sibling_id!r} as an "
                            f"OR-choice sibling, but {sibling_id!r} does not declare "
                            f"{question_id!r} back"
                        ),
                        severity=ValidationSeverity.ERROR,
                        field_path=f"questions[{question_id}].relationships.sibling_or_ids",
                    )
                )

    return issues


def _check_circular_references(graph: RelationshipGraph) -> list[ValidationIssue]:
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        if edge.relationship_type is RelationshipType.PARENT_CHILD:
            children_by_parent[edge.from_id].append(edge.to_id)

    issues: list[ValidationIssue] = []
    reported: set[frozenset[str]] = set()

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = defaultdict(int)

    def visit(node_id: str, path: list[str]) -> None:
        color[node_id] = GRAY
        path.append(node_id)
        for child_id in sorted(children_by_parent.get(node_id, [])):
            if color[child_id] == GRAY:
                cycle = path[path.index(child_id) :] + [child_id]
                key = frozenset(cycle)
                if key not in reported:
                    reported.add(key)
                    issues.append(
                        ValidationIssue(
                            code="CIRCULAR_REFERENCE",
                            message=f"circular parent-child reference: {' -> '.join(cycle)}",
                            severity=ValidationSeverity.ERROR,
                            field_path="relationships",
                        )
                    )
            elif color[child_id] == WHITE:
                visit(child_id, path)
        path.pop()
        color[node_id] = BLACK

    for node in sorted(children_by_parent):
        if color[node] == WHITE:
            visit(node, [])

    return issues
