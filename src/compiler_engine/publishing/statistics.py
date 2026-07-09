"""Computes publishing statistics purely by reading already-registered artifacts —
never re-runs any validation, never re-derives anything Sprint 3-6 already decided.
No analytics, no student data: every number here answers "what happened during this
compilation," not "how are students performing."
"""

from __future__ import annotations

from compiler_engine.domain.cko import CKO
from compiler_engine.domain.relationship_graph import RelationshipGraph
from compiler_engine.domain.validation_report import ValidationReport, ValidationSeverity
from compiler_engine.paper_import.schema import PaperImport, RawQuestion
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.publishing.models import ExportStatistics


def compute_statistics(context: CompilerContext) -> ExportStatistics:
    papers = context.registry.all(PaperImport)
    questions = context.registry.all(RawQuestion)
    ckos = context.registry.all(CKO)

    duplicate_questions_merged = max(0, len(questions) - len(ckos))
    orphan_relationships_skipped = _count_orphan_references(context)
    validation_warnings, validation_errors = _count_validation_issues(context)

    return ExportStatistics(
        papers_processed=len(papers),
        questions_imported=len(questions),
        ckos_created=len(ckos),
        duplicate_questions_merged=duplicate_questions_merged,
        orphan_relationships_skipped=orphan_relationships_skipped,
        validation_warnings=validation_warnings,
        validation_errors=validation_errors,
    )


def _count_orphan_references(context: CompilerContext) -> int:
    return sum(
        1
        for graph in context.registry.all(RelationshipGraph)
        for node in graph.nodes
        if not node.is_resolved
    )


def _count_validation_issues(context: CompilerContext) -> tuple[int, int]:
    warnings = 0
    errors = 0
    for report in context.registry.all(ValidationReport):
        for issue in report.issues:
            if issue.severity is ValidationSeverity.WARNING:
                warnings += 1
            elif issue.severity is ValidationSeverity.ERROR:
                errors += 1
    return warnings, errors
