from datetime import datetime, timezone

import pytest

from compiler_engine.core.errors import SchemaError
from compiler_engine.domain.canonical_knowledge_object import (
    CanonicalKnowledgeObject,
    Provenance,
)
from compiler_engine.domain.educational_analysis import EducationalAnalysis
from compiler_engine.domain.question_ir import QuestionIR


def _sample_cko() -> CanonicalKnowledgeObject:
    return CanonicalKnowledgeObject(
        object_id="cko1",
        question=QuestionIR(
            question_id="q1",
            source_document_id="doc1",
            stem="What is 2+2?",
            question_type="mcq",
        ),
        educational_analysis=EducationalAnalysis(
            question_id="q1", subject="Math", topic="Arithmetic"
        ),
        taxonomy_tags=("math", "arithmetic"),
        provenance=Provenance(
            source_file="paper.pdf",
            extracted_at=datetime.now(timezone.utc),
            engine_version="0.1.0",
        ),
        created_at=datetime.now(timezone.utc),
    )


def test_builds_a_complete_knowledge_object():
    cko = _sample_cko()
    assert cko.question.question_id == "q1"
    assert cko.educational_analysis.subject == "Math"


def test_round_trips_through_json():
    cko = _sample_cko()
    assert CanonicalKnowledgeObject.from_json(cko.to_json()) == cko


def test_rejects_missing_provenance():
    with pytest.raises(SchemaError):
        CanonicalKnowledgeObject.from_dict(
            {
                "object_id": "cko1",
                "question": {
                    "question_id": "q1",
                    "source_document_id": "doc1",
                    "stem": "What is 2+2?",
                    "question_type": "mcq",
                },
                "educational_analysis": {
                    "question_id": "q1",
                    "subject": "Math",
                    "topic": "Arithmetic",
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
