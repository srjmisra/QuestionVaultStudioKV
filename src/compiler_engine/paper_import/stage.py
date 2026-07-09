"""PaperImportStage: the first real pipeline stage. Loads paper.json, validates it
structurally (via PaperImport parsing) and against business rules (via validate_paper),
registers the paper, every individual question, and the ValidationReport in the
ArtifactRegistry, and stops there — no Educational Analysis, Relationship Resolution,
CKO Generation, or export happens here.

A stage-level SUCCESS means "this file was loaded and validated," not "this paper is
free of problems." A paper with validation errors (e.g. a dangling relationship
reference) still produces StageResult.ok() — the ValidationReport carries is_valid=False
and the specific issues, exactly as it's meant to. Only a paper that can't be parsed at
all (malformed JSON, missing required fields, unrecognized block types) fails the stage.
"""

from __future__ import annotations

from datetime import datetime, timezone

from compiler_engine.core.errors import CompilerImportError, SchemaError
from compiler_engine.domain.validation_report import ValidationReport, ValidationSeverity
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.pipeline.stage import PipelineStage, StageResult
from compiler_engine.paper_import.schema import PaperImport
from compiler_engine.paper_import.validation import validate_paper


class PaperImportStage(PipelineStage):
    stage_name = "paper_import"

    def validate_inputs(self, context: CompilerContext) -> None:
        if context.current_document is None:
            raise CompilerImportError("No paper.json path set on context.current_document")
        if not context.current_document.is_file():
            raise CompilerImportError(
                f"paper.json not found: {context.current_document}",
                details={"path": str(context.current_document)},
            )

    def execute(self, context: CompilerContext) -> StageResult:
        assert context.current_document is not None  # enforced by validate_inputs

        try:
            raw_text = context.current_document.read_text(encoding="utf-8")
        except OSError as exc:
            raise CompilerImportError(
                f"Could not read paper.json: {context.current_document}",
                details={"path": str(context.current_document), "reason": str(exc)},
            ) from exc

        try:
            paper = PaperImport.from_json(raw_text)
        except SchemaError as exc:
            return StageResult.fail(self.stage_name, errors=(str(exc),))

        issues = validate_paper(paper)
        is_valid = not any(issue.severity is ValidationSeverity.ERROR for issue in issues)
        report = ValidationReport(
            target_id=paper.paper_id,
            is_valid=is_valid,
            issues=issues,
            generated_at=datetime.now(timezone.utc),
        )

        artifact_ids = [context.registry.register(paper, artifact_id=paper.paper_id)]
        for question in paper.questions:
            composite_id = f"{paper.paper_id}::{question.identity.question_id}"
            artifact_ids.append(context.registry.register(question, artifact_id=composite_id))
        artifact_ids.append(context.registry.register(report, artifact_id=paper.paper_id))

        warnings: tuple[str, ...] = ()
        if not is_valid:
            error_count = sum(1 for issue in issues if issue.severity is ValidationSeverity.ERROR)
            warnings = (
                f"Validation found {error_count} error(s) for paper {paper.paper_id!r}; "
                "see the registered ValidationReport for details.",
            )

        return StageResult.ok(
            self.stage_name, artifact_ids=tuple(artifact_ids), warnings=warnings
        )
