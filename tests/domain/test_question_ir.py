import pytest

from compiler_engine.core.errors import SchemaError
from compiler_engine.domain.answer_ir import AnswerIR
from compiler_engine.domain.question_ir import QuestionIR


def test_builds_a_question_with_nested_sub_questions():
    sub_question = QuestionIR(
        question_id="q1a",
        source_document_id="doc1",
        stem="Part (a)",
        question_type="subjective",
    )
    question = QuestionIR(
        question_id="q1",
        source_document_id="doc1",
        stem="Answer the following.",
        question_type="subjective",
        sub_questions=(sub_question,),
        answer=AnswerIR(answer_type="descriptive", descriptive_answer="42"),
    )
    assert question.sub_questions[0].question_id == "q1a"
    assert question.answer.descriptive_answer == "42"


def test_round_trips_through_json():
    question = QuestionIR(
        question_id="q1",
        source_document_id="doc1",
        stem="What is 2+2?",
        question_type="mcq",
        marks=1,
    )
    assert QuestionIR.from_json(question.to_json()) == question


def test_rejects_missing_stem():
    with pytest.raises(SchemaError):
        QuestionIR.from_dict(
            {
                "question_id": "q1",
                "source_document_id": "doc1",
                "question_type": "mcq",
            }
        )
