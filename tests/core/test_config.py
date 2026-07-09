from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from compiler_engine.core.config import CompilerConfig
from compiler_engine.core.errors import ConfigurationError
from compiler_engine.core.schema_versions import CURRENT_SCHEMA_VERSIONS


def test_accepts_plain_strings_for_path_fields():
    config = CompilerConfig(
        import_workspace="/tmp/import",
        assets_folder="/tmp/assets",
        output_folder="/tmp/output",
    )
    assert config.import_workspace == Path("/tmp/import")


def test_defaults_to_current_schema_versions():
    config = CompilerConfig(
        import_workspace="/tmp/import",
        assets_folder="/tmp/assets",
        output_folder="/tmp/output",
    )
    assert config.schema_versions == CURRENT_SCHEMA_VERSIONS


def test_rejects_empty_path():
    with pytest.raises(PydanticValidationError):
        CompilerConfig(import_workspace="", assets_folder="/tmp/a", output_folder="/tmp/o")


def test_rejects_invalid_log_level():
    with pytest.raises(PydanticValidationError):
        CompilerConfig(
            import_workspace="/tmp/import",
            assets_folder="/tmp/assets",
            output_folder="/tmp/output",
            log_level="VERBOSE",
        )


def test_from_json_file_round_trips(tmp_path):
    config_path = tmp_path / "config.json"
    original = CompilerConfig(
        import_workspace=tmp_path / "import",
        assets_folder=tmp_path / "assets",
        output_folder=tmp_path / "output",
    )
    config_path.write_text(original.to_json(), encoding="utf-8")

    loaded = CompilerConfig.from_json_file(config_path)
    assert loaded == original


def test_from_json_file_missing_file_raises_configuration_error(tmp_path):
    with pytest.raises(ConfigurationError):
        CompilerConfig.from_json_file(tmp_path / "missing.json")


def test_from_json_file_malformed_content_raises_configuration_error(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"import_workspace": "/tmp/import"}', encoding="utf-8")

    with pytest.raises(ConfigurationError):
        CompilerConfig.from_json_file(config_path)
