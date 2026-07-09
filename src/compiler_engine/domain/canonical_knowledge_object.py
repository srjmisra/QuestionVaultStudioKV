"""Canonical Knowledge Object: the final, published-ready artifact that aggregates a
question's IR, its educational analysis, and provenance. This is the artifact the JSON
handoff to the KV Coders Admin Module is built from.
"""

from __future__ import annotations

from datetime import datetime

from compiler_engine.core.base_model import CompilerBaseModel
from compiler_engine.core.schema_versions import CURRENT_SCHEMA_VERSIONS
from compiler_engine.domain.educational_analysis import EducationalAnalysis
from compiler_engine.domain.question_ir import QuestionIR


class Provenance(CompilerBaseModel):
    source_file: str
    page_start: int | None = None
    page_end: int | None = None
    extracted_at: datetime
    engine_version: str


class CanonicalKnowledgeObject(CompilerBaseModel):
    schema_version: str = CURRENT_SCHEMA_VERSIONS["canonical_knowledge_object"]
    object_id: str
    question: QuestionIR
    educational_analysis: EducationalAnalysis
    taxonomy_tags: tuple[str, ...] = ()
    provenance: Provenance
    created_at: datetime
