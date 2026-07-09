"""Canonical Knowledge Object (original Sprint 1 design), wrapping QuestionIR with a
single Provenance record.

DEPRECATED, UNUSED: Sprint 6 specified a real CKO with a fundamentally different shape
(a growable occurrence lineage rather than one Provenance, resolved CKO-to-CKO
relationships, version/checksum/status identity fields, and evolution/usage tracking) —
this model, designed before any of that was known, can't represent it without dropping
data. The real, actively-used artifact is `compiler_engine.domain.cko.CKO`, a
deliberately different name so it doesn't collide with this one. Kept, not deleted, for
the same reason as `document_ast.DocumentAST`: nothing currently produces or consumes
this, but deleting still-referenced-by-name history isn't this stage's call to make.
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
