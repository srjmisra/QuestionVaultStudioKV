import pytest

from compiler_engine.core.errors import ArtifactError
from compiler_engine.domain.question_ir import QuestionIR
from compiler_engine.domain.educational_analysis import EducationalAnalysis
from compiler_engine.pipeline.registry import ArtifactRegistry


def _question(question_id: str = "q1") -> QuestionIR:
    return QuestionIR(
        question_id=question_id,
        source_document_id="doc1",
        stem="What is 2+2?",
        question_type="mcq",
    )


def test_register_then_get_returns_the_same_artifact():
    registry = ArtifactRegistry()
    question = _question()
    registry.register(question, artifact_id="q1")

    assert registry.get(QuestionIR, "q1") == question


def test_get_missing_artifact_raises_artifact_error():
    registry = ArtifactRegistry()
    with pytest.raises(ArtifactError):
        registry.get(QuestionIR, "missing")


def test_register_duplicate_id_raises_artifact_error():
    registry = ArtifactRegistry()
    registry.register(_question(), artifact_id="q1")

    with pytest.raises(ArtifactError):
        registry.register(_question(), artifact_id="q1")


def test_all_returns_only_artifacts_of_the_requested_type():
    registry = ArtifactRegistry()
    registry.register(_question("q1"), artifact_id="q1")
    registry.register(_question("q2"), artifact_id="q2")
    registry.register(
        EducationalAnalysis(question_id="q1", subject="Math", topic="Arithmetic"),
        artifact_id="q1",
    )

    questions = registry.all(QuestionIR)

    assert len(questions) == 2
    assert {q.question_id for q in questions} == {"q1", "q2"}


def test_len_counts_every_registered_artifact_across_types():
    registry = ArtifactRegistry()
    registry.register(_question("q1"), artifact_id="q1")
    registry.register(
        EducationalAnalysis(question_id="q1", subject="Math", topic="Arithmetic"),
        artifact_id="q1",
    )

    assert len(registry) == 2
