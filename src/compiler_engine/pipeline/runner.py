"""PipelineRunner: registers stages and runs them sequentially against a
CompilerContext, timing each one, logging progress, halting on the first failure,
and producing an ExecutionSummary.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace

from compiler_engine.core.errors import CompilerError
from compiler_engine.core.logging import get_logger
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.pipeline.stage import PipelineStage, StageResult, StageStatus


@dataclass(frozen=True)
class ExecutionSummary:
    run_id: str
    results: tuple[StageResult, ...]
    halted: bool
    total_duration_seconds: float

    @property
    def succeeded(self) -> bool:
        return not self.halted and all(result.succeeded for result in self.results)


class PipelineRunner:
    def __init__(self) -> None:
        self._stages: list[PipelineStage] = []
        self._logger = get_logger("pipeline_runner")

    def register(self, stage: PipelineStage) -> "PipelineRunner":
        self._stages.append(stage)
        return self

    @property
    def stages(self) -> tuple[PipelineStage, ...]:
        return tuple(self._stages)

    def run(self, context: CompilerContext) -> ExecutionSummary:
        results: list[StageResult] = []
        halted = False
        run_started = time.monotonic()

        for stage in self._stages:
            logger = context.logger_for(stage.stage_name)
            logger.info("stage started")
            stage_started = time.monotonic()

            try:
                stage.validate_inputs(context)
                result = stage.execute(context)
                stage.validate_outputs(context, result)
            except CompilerError as exc:
                result = StageResult.fail(stage.stage_name, errors=(str(exc),))
            except Exception as exc:  # a bug inside the stage, not an expected failure
                result = StageResult.fail(
                    stage.stage_name, errors=(f"Unexpected error: {exc!r}",)
                )

            result = replace(result, duration_seconds=time.monotonic() - stage_started)
            results.append(result)

            if result.succeeded:
                logger.info(
                    "stage completed",
                    extra={
                        "duration_seconds": result.duration_seconds,
                        "artifact_ids": result.artifact_ids,
                        "warnings": result.warnings,
                    },
                )
            else:
                logger.error(
                    "stage failed",
                    extra={"duration_seconds": result.duration_seconds, "errors": result.errors},
                )
                halted = True
                break

        return ExecutionSummary(
            run_id=context.metadata.run_id,
            results=tuple(results),
            halted=halted,
            total_duration_seconds=time.monotonic() - run_started,
        )
