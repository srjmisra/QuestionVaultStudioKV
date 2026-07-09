"""RelationshipGraph: the resolved parent-child/OR-choice structure for one paper's
questions, produced by the Relationship Resolution stage from a PaperImport's raw,
per-question `relationships` declarations.

A node's `parent_id`/`child_ids` are always that question's own self-declared values,
copied as-is — never inferred or merged from what some other question claims about it.
Cross-question agreement (does the parent's child_ids actually include this child?) is
exactly what Relationship Resolution's consistency checks validate; this model records
the resolved structure, not a verdict on it. A node with `is_resolved=False` is a
question_id that was referenced by some relationship but has no corresponding question
in the paper (an orphan reference).
"""

from __future__ import annotations

from enum import Enum

from compiler_engine.core.base_model import CompilerBaseModel
from compiler_engine.core.schema_versions import CURRENT_SCHEMA_VERSIONS


class RelationshipType(str, Enum):
    PARENT_CHILD = "parent_child"
    OR_CHOICE = "or_choice"


class RelationshipEdge(CompilerBaseModel):
    """A single resolved relationship.

    For PARENT_CHILD, from_id is the parent and to_id is the child. For OR_CHOICE the
    pair is unordered (there is no "from"/"to" direction) — from_id/to_id are simply
    the two question_ids sorted, so each alternative pair appears exactly once.
    """

    from_id: str
    to_id: str
    relationship_type: RelationshipType


class RelationshipNode(CompilerBaseModel):
    question_id: str
    is_resolved: bool
    parent_id: str | None = None
    child_ids: tuple[str, ...] = ()
    or_choice_group_id: str | None = None


class RelationshipGraph(CompilerBaseModel):
    schema_version: str = CURRENT_SCHEMA_VERSIONS["relationship_graph"]
    paper_id: str
    nodes: tuple[RelationshipNode, ...]
    edges: tuple[RelationshipEdge, ...]
