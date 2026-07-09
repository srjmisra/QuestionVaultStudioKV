import json
from datetime import datetime, timezone

import pytest

from compiler_engine.core.errors import SchemaError
from compiler_engine.domain.cko import (
    CKO,
    CkoEvolution,
    CkoLineage,
    CkoOccurrence,
    CkoRelationships,
    CkoStatus,
)
from compiler_engine.domain.educational_analysis import EducationalAnalysis
from compiler_engine.paper_import.schema import RawContent, TextBlock


def _sample_cko() -> CKO:
    return CKO(
        cko_id="cko_abc123",
        version=1,
        checksum="abc123",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        status=CkoStatus.UNDER_REVIEW,
        classification=EducationalAnalysis(question_id="Q1", subject="Math", topic="Algebra"),
        content=RawContent(blocks=(TextBlock(block_type="text", value="What is 2+2?"),)),
        options=None,
        relationships=CkoRelationships(),
        lineage=CkoLineage(
            occurrences=(
                CkoOccurrence(
                    paper_id="paper1",
                    examination="Board Exam",
                    session="2025-26",
                    region="Delhi",
                    original_question_number="1",
                    allocated_marks=1,
                ),
            )
        ),
        evolution=CkoEvolution(),
    )


def test_builds_a_complete_cko():
    cko = _sample_cko()
    assert cko.status is CkoStatus.UNDER_REVIEW
    assert cko.evolution.usage_count == 0
    assert cko.evolution.empirical_difficulty is None
    assert len(cko.lineage.occurrences) == 1


def test_round_trips_through_json():
    cko = _sample_cko()
    assert CKO.from_json(cko.to_json()) == cko


def test_is_frozen():
    cko = _sample_cko()
    with pytest.raises(Exception):
        cko.status = CkoStatus.PUBLISHED


def _with_field_override(cko: CKO, **overrides) -> str:
    payload = json.loads(cko.to_json())
    payload.update(overrides)
    return json.dumps(payload)


def test_rejects_version_below_one():
    with pytest.raises(SchemaError):
        CKO.from_json(_with_field_override(_sample_cko(), version=0))


def test_rejects_unknown_status():
    with pytest.raises(SchemaError):
        CKO.from_json(_with_field_override(_sample_cko(), status="archived"))
