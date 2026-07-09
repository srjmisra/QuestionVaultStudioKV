"""CompilerContext: the one object passed to every pipeline stage.

Unlike the domain models in ``compiler_engine.domain`` (immutable, JSON-serializable
data contracts), this is a mutable runtime object — it changes shape as a run
progresses (current document, accumulated state) and holds non-serializable things
like a Logger, so it is a plain dataclass rather than a CompilerBaseModel.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from compiler_engine import __version__ as ENGINE_VERSION
from compiler_engine.core.config import CompilerConfig
from compiler_engine.core.logging import get_logger
from compiler_engine.pipeline.registry import ArtifactRegistry
from compiler_engine.pipeline.workspace import WorkspaceManager


@dataclass(frozen=True)
class RuntimeMetadata:
    run_id: str = field(default_factory=lambda: uuid4().hex)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    engine_version: str = ENGINE_VERSION


@dataclass
class CompilerContext:
    config: CompilerConfig
    workspace: WorkspaceManager
    logger: logging.Logger = field(default_factory=lambda: get_logger("pipeline"))
    registry: ArtifactRegistry = field(default_factory=ArtifactRegistry)
    metadata: RuntimeMetadata = field(default_factory=RuntimeMetadata)
    current_document: Path | None = None
    state: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, config: CompilerConfig) -> "CompilerContext":
        return cls(config=config, workspace=WorkspaceManager(config))

    def logger_for(self, stage_name: str) -> logging.Logger:
        return get_logger(stage_name)

    def for_document(self, document: Path) -> "CompilerContext":
        """Return a copy of this context scoped to a different current document,
        sharing the same registry, logger, and metadata.
        """
        return replace(self, current_document=document)
