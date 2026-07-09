"""Compiler-wide configuration: workspace paths, logging, and schema versions."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import ConfigDict, Field, field_validator

from compiler_engine.core.base_model import CompilerBaseModel
from compiler_engine.core.errors import ConfigurationError, SchemaError
from compiler_engine.core.schema_versions import CURRENT_SCHEMA_VERSIONS

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogFormat = Literal["json", "text"]


class CompilerConfig(CompilerBaseModel):
    """Runtime configuration for a single invocation of the compilation engine.

    Unlike the pipeline's domain artifacts, config is operator-supplied, so this
    model relaxes ``strict`` (inherited from CompilerBaseModel) to accept plain
    strings for path fields, e.g. ``CompilerConfig(import_workspace="/some/path", ...)``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    import_workspace: Path
    assets_folder: Path
    output_folder: Path
    log_level: LogLevel = "INFO"
    log_format: LogFormat = "json"
    schema_versions: dict[str, str] = Field(default_factory=lambda: dict(CURRENT_SCHEMA_VERSIONS))

    @field_validator("import_workspace", "assets_folder", "output_folder")
    @classmethod
    def _path_must_not_be_empty(cls, value: Path) -> Path:
        if str(value).strip() in ("", "."):
            raise ValueError("path must not be empty")
        return value

    @classmethod
    def from_json_file(cls, path: Path) -> "CompilerConfig":
        try:
            raw = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigurationError(
                f"Could not read compiler configuration file: {path}",
                details={"path": str(path), "reason": str(exc)},
            ) from exc

        try:
            return cls.from_json(raw)
        except SchemaError as exc:
            raise ConfigurationError(
                f"Compiler configuration file is invalid: {path}",
                details={"path": str(path), **exc.details},
            ) from exc
