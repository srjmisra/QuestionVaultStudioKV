"""PublishingStage: the final stage of the Python Compiler. Converts already-registered
CKOs into a deterministic, on-disk export package for the KV Coders PHP/MySQL Admin
Module to import later. Never connects to MySQL, never talks to the website, never
modifies a CKO — a serialization layer only.
"""

from __future__ import annotations

from datetime import datetime, timezone

from compiler_engine.core.errors import CompilerError
from compiler_engine.domain.cko import CKO
from compiler_engine.paper_import.schema import PaperImport
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.pipeline.stage import PipelineStage, StageResult
from compiler_engine.publishing.models import ExportManifest
from compiler_engine.publishing.statistics import compute_statistics
from compiler_engine.publishing.writer import write_export_package
from compiler_engine import __version__ as COMPILER_VERSION


class PublishingStage(PipelineStage):
    stage_name = "publishing"

    def validate_inputs(self, context: CompilerContext) -> None:
        if not context.registry.all(CKO):
            raise CompilerError(
                "No CKO artifacts registered; run canonical_knowledge_object_generation "
                "before publishing"
            )

    def execute(self, context: CompilerContext) -> StageResult:
        logger = context.logger_for(self.stage_name)
        ckos = context.registry.all(CKO)
        statistics = compute_statistics(context)

        manifest = ExportManifest(
            generated_at=datetime.now(timezone.utc),
            compiler_version=COMPILER_VERSION,
            taxonomy_version=context.state.get("taxonomy_version"),
            paper_count=len(context.registry.all(PaperImport)),
            question_count=statistics.questions_imported,
            cko_count=len(ckos),
        )

        export_dir = write_export_package(
            context.workspace.layout.output_folder, manifest, statistics, ckos
        )
        logger.info("export package written", extra={"path": str(export_dir)})

        artifact_ids = (
            context.registry.register(manifest, artifact_id="export"),
            context.registry.register(statistics, artifact_id="export"),
        )

        return StageResult.ok(self.stage_name, artifact_ids=artifact_ids)
