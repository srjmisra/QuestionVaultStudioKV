import pytest

from compiler_engine.core.config import CompilerConfig
from compiler_engine.core.errors import AssetError, CompilerImportError
from compiler_engine.pipeline.workspace import WorkspaceManager


def _config(tmp_path):
    return CompilerConfig(
        import_workspace=tmp_path / "import",
        assets_folder=tmp_path / "assets",
        output_folder=tmp_path / "output",
    )


def test_initialize_creates_every_folder(tmp_path):
    manager = WorkspaceManager(_config(tmp_path))
    layout = manager.initialize()

    assert layout.import_workspace.is_dir()
    assert layout.assets_folder.is_dir()
    assert layout.output_folder.is_dir()
    assert layout.temp_folder.is_dir()


def test_validate_passes_after_initialize(tmp_path):
    manager = WorkspaceManager(_config(tmp_path))
    manager.initialize()
    manager.validate()  # should not raise


def test_validate_fails_when_import_workspace_missing(tmp_path):
    manager = WorkspaceManager(_config(tmp_path))
    manager.layout.assets_folder.mkdir(parents=True)
    manager.layout.output_folder.mkdir(parents=True)

    with pytest.raises(CompilerImportError):
        manager.validate()


def test_validate_fails_when_assets_folder_missing(tmp_path):
    manager = WorkspaceManager(_config(tmp_path))
    manager.layout.import_workspace.mkdir(parents=True)
    manager.layout.output_folder.mkdir(parents=True)

    with pytest.raises(AssetError):
        manager.validate()


def test_locate_assets_returns_only_files_matching_pattern(tmp_path):
    manager = WorkspaceManager(_config(tmp_path))
    manager.initialize()
    assets_folder = manager.layout.assets_folder
    (assets_folder / "diagram.png").write_text("image bytes")
    (assets_folder / "notes.txt").write_text("notes")
    (assets_folder / "subfolder").mkdir()

    images = manager.locate_assets("*.png")

    assert images == (assets_folder / "diagram.png",)


def test_locate_assets_raises_when_assets_folder_missing(tmp_path):
    manager = WorkspaceManager(_config(tmp_path))
    with pytest.raises(AssetError):
        manager.locate_assets()


def test_clean_temp_removes_files_but_keeps_the_folder(tmp_path):
    manager = WorkspaceManager(_config(tmp_path))
    manager.initialize()
    temp_dir = manager.temp_dir()
    (temp_dir / "scratch.txt").write_text("data")
    (temp_dir / "nested").mkdir()
    (temp_dir / "nested" / "inner.txt").write_text("data")

    manager.clean_temp()

    assert temp_dir.is_dir()
    assert list(temp_dir.iterdir()) == []


def test_clean_temp_is_a_noop_when_temp_folder_missing(tmp_path):
    manager = WorkspaceManager(_config(tmp_path))
    manager.clean_temp()  # should not raise
