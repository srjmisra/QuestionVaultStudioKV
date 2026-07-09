"""Validation Report: the outcome of running business-rule validation over an artifact
(typically a Canonical Knowledge Object). Sprint 1 defines the shape only; the Validation
stage that produces these reports is implemented in a later sprint.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from compiler_engine.core.base_model import CompilerBaseModel
from compiler_engine.core.schema_versions import CURRENT_SCHEMA_VERSIONS


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(CompilerBaseModel):
    code: str
    message: str
    severity: ValidationSeverity
    field_path: str | None = None


class ValidationReport(CompilerBaseModel):
    schema_version: str = CURRENT_SCHEMA_VERSIONS["validation_report"]
    target_id: str
    is_valid: bool
    issues: tuple[ValidationIssue, ...] = ()
    generated_at: datetime
