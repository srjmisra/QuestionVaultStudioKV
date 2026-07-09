"""PipelineStage: the contract every future compilation stage (Paper Import,
Relationship Resolution, ...) implements, and StageResult, the strongly typed value
every stage run produces.

Stages report success/failure and their own artifacts/warnings/errors; PipelineRunner
is solely responsible for timing each stage, so stage authors never write timing
boilerplate.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from compiler_engine.pipeline.context import CompilerContext


class StageStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True)
class StageResult:
    stage_name: str
    status: StageStatus
    artifact_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    # Set by PipelineRunner after execute() returns; stages should leave this at 0.0.
    duration_seconds: float = 0.0

    @property
    def succeeded(self) -> bool:
        return self.status is StageStatus.SUCCESS

    @classmethod
    def ok(
        cls,
        stage_name: str,
        *,
        artifact_ids: tuple[str, ...] = (),
        warnings: tuple[str, ...] = (),
    ) -> "StageResult":
        return cls(
            stage_name=stage_name,
            status=StageStatus.SUCCESS,
            artifact_ids=artifact_ids,
            warnings=warnings,
        )

    @classmethod
    def fail(cls, stage_name: str, *, errors: tuple[str, ...]) -> "StageResult":
        return cls(stage_name=stage_name, status=StageStatus.FAILED, errors=errors)


class PipelineStage(ABC):
    """Base class for every pipeline stage. Subclasses must set ``stage_name`` and
    implement ``execute``; ``validate_inputs``/``validate_outputs`` are optional hooks.
    """

    stage_name: ClassVar[str]

    def validate_inputs(self, context: "CompilerContext") -> None:
        """Raise a CompilerError if this stage's required inputs are missing. Default: no-op."""

    @abstractmethod
    def execute(self, context: "CompilerContext") -> StageResult:
        """Do the stage's work and return a StageResult. Must not raise for expected,
        recoverable failures — return ``StageResult.fail(...)`` instead. Unexpected
        exceptions are still caught and recorded by PipelineRunner.
        """

    def validate_outputs(self, context: "CompilerContext", result: StageResult) -> None:
        """Raise a CompilerError if this stage's declared outputs are inconsistent with
        what it actually produced. Default: no-op.
        """
