"""WorkspaceManager: owns the filesystem side of a compilation run — creating and
validating the import workspace, assets, and output folders, and managing the
temporary directory stages may use for intermediate files.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from compiler_engine.core.config import CompilerConfig
from compiler_engine.core.errors import AssetError, CompilerImportError
from compiler_engine.core.logging import get_logger

_TEMP_DIR_NAME = ".tmp"


@dataclass(frozen=True)
class WorkspaceLayout:
    import_workspace: Path
    assets_folder: Path
    output_folder: Path
    temp_folder: Path


class WorkspaceManager:
    def __init__(self, config: CompilerConfig) -> None:
        self._config = config
        self._logger = get_logger("workspace")

    @property
    def layout(self) -> WorkspaceLayout:
        return WorkspaceLayout(
            import_workspace=self._config.import_workspace,
            assets_folder=self._config.assets_folder,
            output_folder=self._config.output_folder,
            temp_folder=self._config.output_folder / _TEMP_DIR_NAME,
        )

    def initialize(self) -> WorkspaceLayout:
        """Create every workspace folder that doesn't exist yet."""
        layout = self.layout
        for folder in (
            layout.import_workspace,
            layout.assets_folder,
            layout.output_folder,
            layout.temp_folder,
        ):
            folder.mkdir(parents=True, exist_ok=True)
            self._logger.info("workspace folder ready", extra={"folder": str(folder)})
        return layout

    def validate(self) -> WorkspaceLayout:
        """Confirm every workspace folder exists and is a directory.

        Raises CompilerImportError for the import workspace (it must already exist and
        contain source material) and AssetError for the assets folder, since those two
        are inputs to the run rather than outputs `initialize()` can create silently.
        """
        layout = self.layout

        if not layout.import_workspace.is_dir():
            raise CompilerImportError(
                f"Import workspace does not exist or is not a directory: {layout.import_workspace}",
                details={"import_workspace": str(layout.import_workspace)},
            )

        if not layout.assets_folder.is_dir():
            raise AssetError(
                f"Assets folder does not exist or is not a directory: {layout.assets_folder}",
                details={"assets_folder": str(layout.assets_folder)},
            )

        if not layout.output_folder.is_dir():
            raise CompilerImportError(
                f"Output folder does not exist or is not a directory: {layout.output_folder}",
                details={"output_folder": str(layout.output_folder)},
            )

        return layout

    def locate_assets(self, pattern: str = "*") -> tuple[Path, ...]:
        assets_folder = self.layout.assets_folder
        if not assets_folder.is_dir():
            raise AssetError(
                f"Assets folder does not exist: {assets_folder}",
                details={"assets_folder": str(assets_folder)},
            )
        return tuple(sorted(p for p in assets_folder.glob(pattern) if p.is_file()))

    def temp_dir(self) -> Path:
        temp_folder = self.layout.temp_folder
        temp_folder.mkdir(parents=True, exist_ok=True)
        return temp_folder

    def clean_temp(self) -> None:
        """Remove everything under the temp folder, keeping the folder itself."""
        temp_folder = self.layout.temp_folder
        if not temp_folder.is_dir():
            return
        for entry in temp_folder.iterdir():
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
        self._logger.info("temp folder cleaned", extra={"folder": str(temp_folder)})
