from datetime import datetime, timezone

import pytest

from compiler_engine.core.errors import SchemaError
from compiler_engine.domain.validation_report import (
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)


def test_builds_a_failing_report_with_issues():
    report = ValidationReport(
        target_id="cko1",
        is_valid=False,
        issues=(
            ValidationIssue(
                code="MISSING_ANSWER",
                message="Question has no answer",
                severity=ValidationSeverity.ERROR,
                field_path="question.answer",
            ),
        ),
        generated_at=datetime.now(timezone.utc),
    )
    assert report.issues[0].severity is ValidationSeverity.ERROR


def test_round_trips_through_json():
    report = ValidationReport(
        target_id="cko1", is_valid=True, generated_at=datetime.now(timezone.utc)
    )
    assert ValidationReport.from_json(report.to_json()) == report


def test_rejects_invalid_severity():
    with pytest.raises(SchemaError):
        ValidationIssue.from_dict(
            {"code": "X", "message": "msg", "severity": "catastrophic"}
        )
