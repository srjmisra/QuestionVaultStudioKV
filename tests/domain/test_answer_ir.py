import pytest

from compiler_engine.core.errors import SchemaError
from compiler_engine.domain.answer_ir import AnswerIR, AnswerOption


def test_builds_a_multi_choice_answer():
    answer = AnswerIR(
        answer_type="single_choice",
        options=(
            AnswerOption(option_id="a", text="2", is_correct=False),
            AnswerOption(option_id="b", text="4", is_correct=True),
        ),
        marks=1,
    )
    assert answer.options[1].is_correct is True


def test_round_trips_through_json():
    answer = AnswerIR(answer_type="descriptive", descriptive_answer="Paris", marks=2)
    assert AnswerIR.from_json(answer.to_json()) == answer


def test_rejects_negative_marks():
    with pytest.raises(SchemaError):
        AnswerIR.from_dict({"answer_type": "descriptive", "marks": -1})
