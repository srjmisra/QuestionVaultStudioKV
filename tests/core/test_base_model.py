import pytest
from pydantic import ValidationError as PydanticValidationError

from compiler_engine.core.base_model import CompilerBaseModel
from compiler_engine.core.errors import SchemaError


class Widget(CompilerBaseModel):
    widget_id: str
    count: int


def test_from_dict_builds_a_valid_model():
    widget = Widget.from_dict({"widget_id": "w1", "count": 3})
    assert widget.widget_id == "w1"
    assert widget.count == 3


def test_from_dict_wraps_invalid_payload_in_schema_error():
    with pytest.raises(SchemaError):
        Widget.from_dict({"widget_id": "w1"})


def test_from_json_round_trips_with_to_json():
    original = Widget(widget_id="w1", count=3)
    restored = Widget.from_json(original.to_json())
    assert restored == original


def test_from_json_wraps_invalid_payload_in_schema_error():
    with pytest.raises(SchemaError):
        Widget.from_json('{"widget_id": "w1"}')


def test_to_dict_round_trips_with_from_dict():
    original = Widget(widget_id="w1", count=3)
    assert Widget.from_dict(original.to_dict()) == original


def test_models_are_frozen():
    widget = Widget(widget_id="w1", count=3)
    with pytest.raises(PydanticValidationError):
        widget.count = 4


def test_unknown_fields_are_rejected():
    with pytest.raises(SchemaError):
        Widget.from_dict({"widget_id": "w1", "count": 3, "unexpected": "field"})
