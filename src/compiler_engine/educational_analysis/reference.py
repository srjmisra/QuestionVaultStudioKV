"""Lookup indices built from the canonical reference taxonomies this stage validates
paper.json's raw classification against.

Two Taxonomy instances (Sprint 1's existing, generic domain model — reused unmodified,
not redesigned) are expected in the ArtifactRegistry before this stage runs:

- taxonomy_id == "curriculum": a chapter -> topic -> concept tree, grouped under
  top-level "unit" nodes. Depth is derived from actual tree position during traversal,
  not from each node's own `level` field, so a mis-authored `level` value can't corrupt
  the index. Units are never checked against individual questions, because paper.json's
  classification has no `unit` field to check them against — a chapter resolving in this
  index at all already implies it has a unit parent, since that's how the tree is built.
- taxonomy_id == "question_types": a flat, one-level list of valid question_type nodes.

Neither of these is invented here, and this module never fabricates one — see
EducationalAnalysisStage.validate_inputs for what happens when they're missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from compiler_engine.domain.taxonomy import Taxonomy, TaxonomyNode

CURRICULUM_TAXONOMY_ID = "curriculum"
QUESTION_TYPES_TAXONOMY_ID = "question_types"

_CHAPTER_DEPTH = 1
_TOPIC_DEPTH = 2
_CONCEPT_DEPTH = 3


@dataclass(frozen=True)
class CurriculumIndex:
    chapter_ids: frozenset[str] = frozenset()
    topic_ids: frozenset[str] = frozenset()
    concept_ids: frozenset[str] = frozenset()
    chapter_of_topic: dict[str, str] = field(default_factory=dict)
    topic_of_concept: dict[str, str] = field(default_factory=dict)


def build_curriculum_index(curriculum: Taxonomy) -> CurriculumIndex:
    chapter_ids: set[str] = set()
    topic_ids: set[str] = set()
    concept_ids: set[str] = set()
    chapter_of_topic: dict[str, str] = {}
    topic_of_concept: dict[str, str] = {}

    def visit(node: TaxonomyNode, parent_id: str | None, depth: int) -> None:
        if depth == _CHAPTER_DEPTH:
            chapter_ids.add(node.node_id)
        elif depth == _TOPIC_DEPTH:
            topic_ids.add(node.node_id)
            if parent_id is not None:
                chapter_of_topic[node.node_id] = parent_id
        elif depth == _CONCEPT_DEPTH:
            concept_ids.add(node.node_id)
            if parent_id is not None:
                topic_of_concept[node.node_id] = parent_id
        for child in node.children:
            visit(child, node.node_id, depth + 1)

    for root in curriculum.roots:
        visit(root, None, depth=0)

    return CurriculumIndex(
        chapter_ids=frozenset(chapter_ids),
        topic_ids=frozenset(topic_ids),
        concept_ids=frozenset(concept_ids),
        chapter_of_topic=chapter_of_topic,
        topic_of_concept=topic_of_concept,
    )


def question_type_ids(question_types: Taxonomy) -> frozenset[str]:
    return frozenset(node.node_id for node in question_types.roots)
