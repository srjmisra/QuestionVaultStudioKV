import pytest
from pydantic import BaseModel

from compiler_engine.core.errors import (
    AssetError,
    CompilerError,
    CompilerImportError,
    ConfigurationError,
    SchemaError,
    ValidationError,
)


def test_compiler_error_str_without_details():
    err = CompilerError("something broke")
    assert str(err) == "something broke"


def test_compiler_error_str_with_details():
    err = CompilerError("something broke", details={"stage": "paper_import"})
    assert str(err) == "something broke (stage='paper_import')"


@pytest.mark.parametrize(
    "error_cls",
    [SchemaError, ValidationError, CompilerImportError, AssetError, ConfigurationError],
)
def test_every_error_is_a_compiler_error(error_cls):
    assert issubclass(error_cls, CompilerError)


def test_compiler_import_error_does_not_shadow_builtin():
    assert CompilerImportError is not ImportError
    assert not issubclass(CompilerImportError, ImportError)


def test_schema_error_from_pydantic_describes_every_field():
    class Dummy(BaseModel):
        name: str
        age: int

    with pytest.raises(Exception) as exc_info:
        Dummy.model_validate({"age": "not-a-number"})
    schema_error = SchemaError.from_pydantic("Dummy", exc_info.value)

    assert "Dummy failed schema validation" in schema_error.message
    field_paths = {e["field_path"] for e in schema_error.details["errors"]}
    assert "name" in field_paths
    assert "age" in field_paths
