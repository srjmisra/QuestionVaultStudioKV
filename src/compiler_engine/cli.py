"""Compiler CLI entry point.

Loads configuration, initializes and validates the workspace, builds a CompilerContext,
runs the pipeline, and prints an execution summary. As of Sprint 3, the pipeline runs
PaperImportStage when ``--paper`` is given; later sprints will register further stages
(Relationship Resolution, CKO Generation, ...) the same way, before ``runner.run(...)``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from compiler_engine.core.config import CompilerConfig
from compiler_engine.core.errors import CompilerError
from compiler_engine.core.logging import configure_logging, get_logger
from compiler_engine.paper_import.stage import PaperImportStage
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.pipeline.runner import ExecutionSummary, PipelineRunner
from compiler_engine.pipeline.workspace import WorkspaceManager


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="qv_compile", description="QuestionVault Studio compiler")
    parser.add_argument("--config", type=Path, help="Path to a CompilerConfig JSON file")
    parser.add_argument("--import-workspace", type=Path)
    parser.add_argument("--assets-folder", type=Path)
    parser.add_argument("--output-folder", type=Path)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-format", default="json", choices=["json", "text"])
    parser.add_argument("--paper", type=Path, help="Path to a paper.json file to import")
    return parser.parse_args(argv)


def _build_config(args: argparse.Namespace) -> CompilerConfig:
    if args.config:
        return CompilerConfig.from_json_file(args.config)

    missing = [
        name
        for name, value in (
            ("--import-workspace", args.import_workspace),
            ("--assets-folder", args.assets_folder),
            ("--output-folder", args.output_folder),
        )
        if value is None
    ]
    if missing:
        raise CompilerError(
            "Either --config or all of --import-workspace/--assets-folder/--output-folder "
            "must be provided",
            details={"missing": missing},
        )

    return CompilerConfig(
        import_workspace=args.import_workspace,
        assets_folder=args.assets_folder,
        output_folder=args.output_folder,
        log_level=args.log_level,
        log_format=args.log_format,
    )


def _print_summary(summary: ExecutionSummary) -> None:
    print(f"Run {summary.run_id}")
    print(f"  status: {'SUCCESS' if summary.succeeded else 'HALTED' if summary.halted else 'FAILED'}")
    print(f"  total duration: {summary.total_duration_seconds:.3f}s")
    print(f"  stages run: {len(summary.results)}")
    for result in summary.results:
        marker = "OK" if result.succeeded else "FAILED"
        print(f"    [{marker}] {result.stage_name} ({result.duration_seconds:.3f}s)")
        for warning in result.warnings:
            print(f"        warning: {warning}")
        for error in result.errors:
            print(f"        error: {error}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        config = _build_config(args)
        configure_logging(level=config.log_level, format=config.log_format)
        logger = get_logger("cli")

        workspace = WorkspaceManager(config)
        workspace.initialize()
        workspace.validate()
        logger.info("workspace ready", extra={"layout": str(workspace.layout)})

        context = CompilerContext.create(config)
        if args.paper:
            context = context.for_document(args.paper)

        runner = PipelineRunner()
        if args.paper:
            runner.register(PaperImportStage())
        # Future sprints: runner.register(RelationshipResolutionStage()) etc., here too.
        summary = runner.run(context)
    except CompilerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _print_summary(summary)
    return 0 if summary.succeeded else 1


if __name__ == "__main__":
    sys.exit(main())
