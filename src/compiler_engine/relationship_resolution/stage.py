"""RelationshipResolutionStage: consumes the PaperImport artifacts paper_import
registered (never paper.json directly, and never modifies paper_import), builds a
RelationshipGraph per paper, validates it, and registers the graph plus a Relationship
Resolution Report (a ValidationReport, registered under "{paper_id}::relationships" so
it doesn't collide with paper_import's own "{paper_id}" ValidationReport).

Like PaperImportStage, a stage-level SUCCESS means "a graph was built and checked," not
"the relationships are clean" — orphans, inconsistencies, and cycles are recorded in the
report, not raised as stage failures.
"""

from __future__ import annotations

from datetime import datetime, timezone

from compiler_engine.core.errors import CompilerError
from compiler_engine.domain.validation_report import ValidationReport, ValidationSeverity
from compiler_engine.paper_import.schema import PaperImport
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.pipeline.stage import PipelineStage, StageResult
from compiler_engine.relationship_resolution.graph import build_graph, detect_issues


class RelationshipResolutionStage(PipelineStage):
    stage_name = "relationship_resolution"

    def validate_inputs(self, context: CompilerContext) -> None:
        if not context.registry.all(PaperImport):
            raise CompilerError(
                "No PaperImport artifacts registered; run paper_import before "
                "relationship_resolution"
            )

    def execute(self, context: CompilerContext) -> StageResult:
        artifact_ids: list[str] = []
        warnings: list[str] = []

        for paper in context.registry.all(PaperImport):
            graph = build_graph(paper)
            issues = detect_issues(paper, graph)
            is_valid = not any(issue.severity is ValidationSeverity.ERROR for issue in issues)
            report = ValidationReport(
                target_id=paper.paper_id,
                is_valid=is_valid,
                issues=issues,
                generated_at=datetime.now(timezone.utc),
            )

            artifact_ids.append(context.registry.register(graph, artifact_id=paper.paper_id))
            artifact_ids.append(
                context.registry.register(report, artifact_id=f"{paper.paper_id}::relationships")
            )

            if not is_valid:
                error_count = sum(
                    1 for issue in issues if issue.severity is ValidationSeverity.ERROR
                )
                warnings.append(
                    f"Relationship resolution found {error_count} error(s) for paper "
                    f"{paper.paper_id!r}; see the registered Relationship Resolution "
                    "Report for details."
                )

        return StageResult.ok(
            self.stage_name, artifact_ids=tuple(artifact_ids), warnings=tuple(warnings)
        )
