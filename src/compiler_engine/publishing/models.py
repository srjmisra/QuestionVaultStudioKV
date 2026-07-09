"""Manifest and statistics shapes for the export package. Deliberately NOT in
`domain/`: nothing else in this compiler consumes them — they're this stage's own
terminal output, produced for an external consumer (the KV Coders PHP Admin Module),
not a contract other compiler stages need to understand. That's the same reasoning
that kept paper_import's RawQuestion out of domain/ in Sprint 3.
"""

from __future__ import annotations

from datetime import datetime

from compiler_engine.core.base_model import CompilerBaseModel

EXPORT_FORMAT_VERSION = "1.0"

# Must match the algorithm compiler_engine.canonical_knowledge_object_generation
# .checksum.compute_checksum actually uses (hashlib.sha256). Not imported from there:
# this is a descriptive label for the manifest, not the hashing code itself, and Sprint
# 6 is frozen -- this constant is duplicated rather than reached into.
CHECKSUM_ALGORITHM = "sha256"


class ExportManifest(CompilerBaseModel):
    export_version: str = EXPORT_FORMAT_VERSION
    generated_at: datetime
    compiler_version: str
    taxonomy_version: str | None = None
    paper_count: int
    question_count: int
    cko_count: int
    checksum_algorithm: str = CHECKSUM_ALGORITHM


class ExportStatistics(CompilerBaseModel):
    papers_processed: int
    questions_imported: int
    ckos_created: int
    duplicate_questions_merged: int
    orphan_relationships_skipped: int
    validation_warnings: int
    validation_errors: int
