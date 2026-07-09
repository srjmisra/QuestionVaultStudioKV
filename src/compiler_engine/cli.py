"""Compiler CLI entry point.

Loads configuration, initializes and validates the workspace, builds a CompilerContext,
runs the pipeline, and prints an execution summary. As of Sprint 5, the pipeline runs
PaperImportStage, RelationshipResolutionStage, and (only if ``--taxonomy`` is also
given) EducationalAnalysisStage, when ``--paper`` is given; later sprints will register
further stages (CKO Generation, ...) the same way, before ``runner.run(...)``.

``--taxonomy`` points at a JSON file this CLI invented the shape of (no such loading
convention existed before Sprint 5, since nothing previously needed reference data
rather than paper.json itself): a dict of named Taxonomy objects, keyed by taxonomy_id,
e.g. ``{"curriculum": {...}, "question_types": {...}}``. It is never a substitute for
the real "QuestionVault Taxonomy v1.0" content, which this codebase does not invent.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from compiler_engine.core.config import CompilerConfig
from compiler_engine.core.errors import CompilerError, SchemaError
from compiler_engine.core.logging import configure_logging, get_logger
from compiler_engine.domain.taxonomy import Taxonomy
from compiler_engine.educational_analysis.stage import EducationalAnalysisStage
from compiler_engine.paper_import.stage import PaperImportStage
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.pipeline.runner import ExecutionSummary, PipelineRunner
from compiler_engine.pipeline.workspace import WorkspaceManager
from compiler_engine.relationship_resolution.stage import RelationshipResolutionStage


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="qv_compile", description="QuestionVault Studio compiler")
    parser.add_argument("--config", type=Path, help="Path to a CompilerConfig JSON file")
    parser.add_argument("--import-workspace", type=Path)
    parser.add_argument("--assets-folder", type=Path)
    parser.add_argument("--output-folder", type=Path)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-format", default="json", choices=["json", "text"])
    parser.add_argument("--paper", type=Path, help="Path to a paper.json file to import")
    parser.add_argument(
        "--taxonomy",
        type=Path,
        help="Path to a JSON file of named reference Taxonomy objects (curriculum, question_types)",
    )
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


def _load_taxonomies(path: Path) -> dict[str, Taxonomy]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CompilerError(
            f"Could not read taxonomy file: {path}",
            details={"path": str(path), "reason": str(exc)},
        ) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CompilerError(
            f"Taxonomy file is not valid JSON: {path}", details={"path": str(path)}
        ) from exc

    try:
        return {name: Taxonomy.from_json(json.dumps(value)) for name, value in payload.items()}
    except SchemaError as exc:
        raise CompilerError(
            f"Taxonomy file is invalid: {path}", details={"path": str(path), **exc.details}
        ) from exc


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

        if args.taxonomy:
            for name, taxonomy in _load_taxonomies(args.taxonomy).items():
                context.registry.register(taxonomy, artifact_id=name)

        runner = PipelineRunner()
        if args.paper:
            runner.register(PaperImportStage()).register(RelationshipResolutionStage())
            if args.taxonomy:
                runner.register(EducationalAnalysisStage())
        # Future sprints: runner.register(CkoGenerationStage()) etc., here too.
        summary = runner.run(context)
    except CompilerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _print_summary(summary)
    return 0 if summary.succeeded else 1


if __name__ == "__main__":
    sys.exit(main())
