"""Taxonomy: the subject/topic/subtopic tree that Educational Analysis tags reference."""

from __future__ import annotations

from compiler_engine.core.base_model import CompilerBaseModel
from compiler_engine.core.schema_versions import CURRENT_SCHEMA_VERSIONS


class TaxonomyNode(CompilerBaseModel):
    node_id: str
    name: str
    level: int
    children: tuple["TaxonomyNode", ...] = ()


class Taxonomy(CompilerBaseModel):
    schema_version: str = CURRENT_SCHEMA_VERSIONS["taxonomy"]
    taxonomy_id: str
    name: str
    roots: tuple[TaxonomyNode, ...]
