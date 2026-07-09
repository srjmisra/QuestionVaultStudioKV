import pytest

from compiler_engine.core.errors import SchemaError
from compiler_engine.domain.educational_analysis import (
    BloomLevel,
    DifficultyLevel,
    EducationalAnalysis,
)


def test_builds_a_classified_analysis():
    analysis = EducationalAnalysis(
        question_id="q1",
        subject="Computer Science",
        topic="Programming",
        subtopic="Loops",
        difficulty=DifficultyLevel.MEDIUM,
        bloom_level=BloomLevel.APPLY,
        keywords=("for-loop", "iteration"),
        taxonomy_path=("Computer Science", "Programming", "Loops"),
    )
    assert analysis.difficulty is DifficultyLevel.MEDIUM
    assert "for-loop" in analysis.keywords


def test_round_trips_through_json():
    analysis = EducationalAnalysis(question_id="q1", subject="Math", topic="Algebra")
    assert EducationalAnalysis.from_json(analysis.to_json()) == analysis


def test_rejects_invalid_difficulty():
    with pytest.raises(SchemaError):
        EducationalAnalysis.from_dict(
            {
                "question_id": "q1",
                "subject": "Math",
                "topic": "Algebra",
                "difficulty": "impossible",
            }
        )
