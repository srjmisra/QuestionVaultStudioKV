"""Project-wide error hierarchy for the Python Compilation Engine."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError as PydanticValidationError


class CompilerError(Exception):
    """Base class for every error raised by the compilation engine."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if not self.details:
            return self.message
        formatted_details = ", ".join(f"{key}={value!r}" for key, value in self.details.items())
        return f"{self.message} ({formatted_details})"


class SchemaError(CompilerError):
    """A JSON/dict payload did not conform to a domain model's schema."""

    @classmethod
    def from_pydantic(cls, model_name: str, exc: PydanticValidationError) -> "SchemaError":
        field_errors = [
            {
                "field_path": ".".join(str(part) for part in error["loc"]) or "<root>",
                "message": error["msg"],
                "input": error.get("input"),
            }
            for error in exc.errors()
        ]
        summary = "; ".join(f"{fe['field_path']}: {fe['message']}" for fe in field_errors)
        return cls(
            f"{model_name} failed schema validation: {summary}",
            details={"model": model_name, "errors": field_errors},
        )


class ValidationError(CompilerError):
    """A Canonical Knowledge Object (or other artifact) failed business-rule validation."""


class CompilerImportError(CompilerError):
    """A paper/document import operation could not complete.

    Named ``CompilerImportError`` rather than ``ImportError`` to avoid shadowing the
    built-in ``ImportError``.
    """


class AssetError(CompilerError):
    """An asset (image, attachment, etc.) referenced by an artifact is missing or invalid."""


class ConfigurationError(CompilerError):
    """The compiler configuration is missing or invalid."""


class ArtifactError(CompilerError):
    """An ArtifactRegistry lookup or registration failed (duplicate id, not found, etc.).

    Added in Sprint 2 alongside the ArtifactRegistry; not one of the Sprint 1 examples.
    """
