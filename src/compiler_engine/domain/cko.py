"""CKO: the permanent identity layer. A CKO represents one unique question, independent
of any specific exam paper — every future occurrence of the same question is meant to
point at the same CKO, accumulating in its `lineage` rather than creating a new object.

Named `CKO` rather than `CanonicalKnowledgeObject` so it doesn't collide with the
deprecated Sprint 1 model of that name (`canonical_knowledge_object.py`), which this
supersedes but does not replace in-place.

Content/options embed paper_import's `RawContent`/`RawOption` directly rather than
redefining them — by the time a CKO is built, that data has already passed through
paper_import's structural validation, so "raw" here describes their origin (Gemini's
wire format), not a lack of validation. Preserving them unchanged is the point: Sprint 6
requires the exact block structure, unrewritten wording, and unmerged blocks.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from compiler_engine.core.base_model import CompilerBaseModel
from compiler_engine.core.schema_versions import CURRENT_SCHEMA_VERSIONS
from compiler_engine.domain.educational_analysis import EducationalAnalysis
from compiler_engine.paper_import.schema import RawContent, RawOption


class CkoStatus(str, Enum):
    """The frozen CKO Architecture's review workflow states. CKO generation always
    produces UNDER_REVIEW; nothing in this codebase ever transitions a CKO to any other
    status. (Sprint 6 originally invented PENDING_REVIEW/APPROVED/REJECTED/MERGED here,
    without having seen the real frozen enum — corrected in the Sprint 6 review to match
    it exactly, with no additional states.)
    """

    PUBLISHED = "published"
    UNDER_REVIEW = "under_review"
    DEPRECATED = "deprecated"


class CkoRelationships(CompilerBaseModel):
    parent_cko_id: str | None = None
    child_cko_ids: tuple[str, ...] = ()
    sibling_or_cko_ids: tuple[str, ...] = ()


class CkoOccurrence(CompilerBaseModel):
    """One occurrence of this question in one specific exam paper."""

    paper_id: str
    examination: str
    session: str
    region: str
    original_question_number: str
    allocated_marks: int | None = Field(
        default=None,
        description=(
            "None when the occurrence's section_id doesn't resolve in its paper — the "
            "same graceful-degradation the earlier stages use; a defect here was already "
            "reported by paper_import's ValidationReport, and this stage doesn't "
            "re-report it."
        ),
    )


class CkoLineage(CompilerBaseModel):
    occurrences: tuple[CkoOccurrence, ...]


class CkoEvolution(CompilerBaseModel):
    """Initialized only — nothing in this codebase computes analytics into these fields."""

    usage_count: int = 0
    empirical_difficulty: float | None = None
    average_time_seconds: float | None = None
    editorial_notes: tuple[str, ...] = ()


class CKO(CompilerBaseModel):
    schema_version: str = CURRENT_SCHEMA_VERSIONS["cko"]

    # Identity
    cko_id: str
    version: int = Field(ge=1)
    checksum: str
    created_at: datetime
    updated_at: datetime
    status: CkoStatus

    # Classification — validated educational metadata only, never re-derived here.
    classification: EducationalAnalysis

    # Content — preserved exactly, never rewritten or merged.
    content: RawContent

    # Options — preserved exactly.
    options: tuple[RawOption, ...] | None = None

    relationships: CkoRelationships
    lineage: CkoLineage
    evolution: CkoEvolution
