"""Common base class giving every domain model JSON load/validate/serialize behavior."""

from __future__ import annotations

from typing import Any, Mapping, Self

from pydantic import BaseModel, ConfigDict
from pydantic import ValidationError as PydanticValidationError

from compiler_engine.core.errors import SchemaError


class CompilerBaseModel(BaseModel):
    """Base class for all compiler domain models.

    Frozen and closed to unknown fields, so every model is immutable and rejects
    payloads that don't match its schema exactly, instead of silently ignoring
    unexpected data.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        try:
            return cls.model_validate(data)
        except PydanticValidationError as exc:
            raise SchemaError.from_pydantic(cls.__name__, exc) from exc

    @classmethod
    def from_json(cls, raw: str | bytes) -> Self:
        try:
            return cls.model_validate_json(raw)
        except PydanticValidationError as exc:
            raise SchemaError.from_pydantic(cls.__name__, exc) from exc

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)

    def to_json(self, *, indent: int | None = 2) -> str:
        return self.model_dump_json(indent=indent, by_alias=True)
