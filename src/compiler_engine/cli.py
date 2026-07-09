"""Compiler CLI entry point.

Loads configuration, initializes and validates the workspace, builds a CompilerContext,
runs the pipeline, and prints an execution summary. As of Sprint 7, the pipeline runs
PaperImportStage, RelationshipResolutionStage, and (only if ``--taxonomy`` is also
given) EducationalAnalysisStage, CkoGenerationStage, and PublishingStage, when
``--paper`` is given; later sprints will register further stages the same way, before
``runner.run(...)``.

``--taxonomy`` points at the real, frozen ``reference/taxonomy.json`` (or any file in
that same shape: a ``metadata``/``curriculum``/``question_types`` document, with
``id``/``unit_id``/``chapter_id``/``topic_id`` fields at each curriculum level) and is
converted into the two Taxonomy artifacts EducationalAnalysisStage requires. Sprint 5
originally guessed at a different, simpler shape here before any real taxonomy existed;
this loader was rewritten in Sprint 6 to match the real file once it existed, not the
other way around.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from compiler_engine.canonical_knowledge_object_generation.stage import CkoGenerationStage
from compiler_engine.core.config import CompilerConfig
from compiler_engine.core.errors import CompilerError, SchemaError
from compiler_engine.core.logging import configure_logging, get_logger
from compiler_engine.domain.taxonomy import Taxonomy, TaxonomyNode
from compiler_engine.educational_analysis.reference import (
    CURRICULUM_TAXONOMY_ID,
    QUESTION_TYPES_TAXONOMY_ID,
)
from compiler_engine.educational_analysis.stage import EducationalAnalysisStage
from compiler_engine.paper_import.stage import PaperImportStage
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.pipeline.runner import ExecutionSummary, PipelineRunner
from compiler_engine.pipeline.workspace import WorkspaceManager
from compiler_engine.publishing.stage import PublishingStage
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


def _load_taxonomies(path: Path) -> tuple[dict[str, Taxonomy], str | None]:
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
        curriculum = payload["curriculum"]
        question_types = payload["question_types"]
    except KeyError as exc:
        raise CompilerError(
            f"Taxonomy file is missing a required top-level key: {exc}",
            details={"path": str(path)},
        ) from exc

    # Content version of the taxonomy document itself (e.g. "1.0"), distinct from
    # Taxonomy.schema_version (the wrapper model's own, unrelated versioning). Optional:
    # not every taxonomy file need carry this, so its absence degrades gracefully rather
    # than failing the load.
    taxonomy_version = payload.get("metadata", {}).get("taxonomy_version")

    try:
        curriculum_roots = tuple(_unit_node(unit) for unit in curriculum)
        question_type_roots = tuple(
            TaxonomyNode(node_id=qt["id"], name=qt["name"], level=0) for qt in question_types
        )
    except (KeyError, TypeError) as exc:
        raise CompilerError(
            f"Taxonomy file has an unexpected shape: {exc}", details={"path": str(path)}
        ) from exc

    try:
        taxonomies = {
            CURRICULUM_TAXONOMY_ID: Taxonomy(
                taxonomy_id=CURRICULUM_TAXONOMY_ID, name="curriculum", roots=curriculum_roots
            ),
            QUESTION_TYPES_TAXONOMY_ID: Taxonomy(
                taxonomy_id=QUESTION_TYPES_TAXONOMY_ID,
                name="question_types",
                roots=question_type_roots,
            ),
        }
    except SchemaError as exc:
        raise CompilerError(
            f"Taxonomy file is invalid: {path}", details={"path": str(path), **exc.details}
        ) from exc

    return taxonomies, taxonomy_version


def _unit_node(unit: dict) -> TaxonomyNode:
    return TaxonomyNode(
        node_id=unit["id"],
        name=unit["name"],
        level=0,
        children=tuple(_chapter_node(chapter) for chapter in unit.get("chapters", [])),
    )


def _chapter_node(chapter: dict) -> TaxonomyNode:
    return TaxonomyNode(
        node_id=chapter["id"],
        name=chapter["name"],
        level=1,
        children=tuple(_topic_node(topic) for topic in chapter.get("topics", [])),
    )


def _topic_node(topic: dict) -> TaxonomyNode:
    return TaxonomyNode(
        node_id=topic["id"],
        name=topic["name"],
        level=2,
        children=tuple(
            TaxonomyNode(node_id=concept["id"], name=concept["name"], level=3)
            for concept in topic.get("concepts", [])
        ),
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

        if args.taxonomy:
            taxonomies, taxonomy_version = _load_taxonomies(args.taxonomy)
            for name, taxonomy in taxonomies.items():
                context.registry.register(taxonomy, artifact_id=name)
            context.state["taxonomy_version"] = taxonomy_version

        runner = PipelineRunner()
        if args.paper:
            runner.register(PaperImportStage()).register(RelationshipResolutionStage())
            if args.taxonomy:
                runner.register(EducationalAnalysisStage()).register(CkoGenerationStage())
                runner.register(PublishingStage())
        # Future sprints: register further stages here too.
        summary = runner.run(context)
    except CompilerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _print_summary(summary)
    return 0 if summary.succeeded else 1


if __name__ == "__main__":
    sys.exit(main())
