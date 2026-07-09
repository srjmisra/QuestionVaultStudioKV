"""EducationalAnalysisStage: the compiler's semantic-analysis phase. Reads PaperImport
artifacts already registered by paper_import (never paper.json directly), and the two
canonical reference Taxonomy artifacts this stage requires (see reference.py) — never
invents them. Normalizes classification into EducationalAnalysis objects, verifies it
against the reference taxonomies, and registers both plus a ValidationReport.

Same success semantics as every prior stage: SUCCESS means "analysis was produced and
checked," not "the classification is correct." A wrong chapter/topic/concept/bloom/
difficulty value is reported in the ValidationReport, never corrected.
"""

from __future__ import annotations

from datetime import datetime, timezone

from compiler_engine.core.errors import CompilerError
from compiler_engine.domain.taxonomy import Taxonomy
from compiler_engine.domain.validation_report import ValidationReport, ValidationSeverity
from compiler_engine.educational_analysis.reference import (
    CURRICULUM_TAXONOMY_ID,
    QUESTION_TYPES_TAXONOMY_ID,
    build_curriculum_index,
    question_type_ids,
)
from compiler_engine.educational_analysis.verification import (
    build_educational_analysis,
    detect_issues,
)
from compiler_engine.paper_import.schema import PaperImport
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.pipeline.stage import PipelineStage, StageResult


class EducationalAnalysisStage(PipelineStage):
    stage_name = "educational_analysis"

    def validate_inputs(self, context: CompilerContext) -> None:
        if not context.registry.all(PaperImport):
            raise CompilerError(
                "No PaperImport artifacts registered; run paper_import before "
                "educational_analysis"
            )
        # Raises ArtifactError (a CompilerError) if either reference taxonomy is
        # missing — this stage never fabricates one.
        context.registry.get(Taxonomy, CURRICULUM_TAXONOMY_ID)
        context.registry.get(Taxonomy, QUESTION_TYPES_TAXONOMY_ID)

    def execute(self, context: CompilerContext) -> StageResult:
        curriculum_index = build_curriculum_index(
            context.registry.get(Taxonomy, CURRICULUM_TAXONOMY_ID)
        )
        valid_question_type_ids = question_type_ids(
            context.registry.get(Taxonomy, QUESTION_TYPES_TAXONOMY_ID)
        )

        artifact_ids: list[str] = []
        warnings: list[str] = []

        for paper in context.registry.all(PaperImport):
            analyses = build_educational_analysis(paper)
            issues = detect_issues(paper, curriculum_index, valid_question_type_ids)
            is_valid = not any(issue.severity is ValidationSeverity.ERROR for issue in issues)
            report = ValidationReport(
                target_id=paper.paper_id,
                is_valid=is_valid,
                issues=issues,
                generated_at=datetime.now(timezone.utc),
            )

            for analysis in analyses:
                composite_id = f"{paper.paper_id}::{analysis.question_id}"
                artifact_ids.append(context.registry.register(analysis, artifact_id=composite_id))
            artifact_ids.append(
                context.registry.register(
                    report, artifact_id=f"{paper.paper_id}::educational_analysis"
                )
            )

            if not is_valid:
                error_count = sum(
                    1 for issue in issues if issue.severity is ValidationSeverity.ERROR
                )
                warnings.append(
                    f"Educational analysis verification found {error_count} error(s) "
                    f"for paper {paper.paper_id!r}; see the registered ValidationReport "
                    "for details."
                )

        return StageResult.ok(
            self.stage_name, artifact_ids=tuple(artifact_ids), warnings=tuple(warnings)
        )
