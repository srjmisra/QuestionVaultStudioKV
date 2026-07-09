"""CkoGenerationStage: the final stage this codebase currently implements. Consumes
PaperImport, RelationshipGraph, and EducationalAnalysis artifacts already in the
registry — never paper.json, never re-classifies, never re-resolves relationships —
and registers one CKO per unique question checksum.

Unlike every prior stage, this one does not produce a ValidationReport: it doesn't run
any new verification pass of its own, it mechanically assembles already-validated
inputs. Any defect in those inputs (a dangling relationship, an unknown taxonomy id)
was already reported by the stage that found it.
"""

from __future__ import annotations

from compiler_engine.core.errors import CompilerError
from compiler_engine.domain.educational_analysis import EducationalAnalysis
from compiler_engine.domain.relationship_graph import RelationshipGraph
from compiler_engine.canonical_knowledge_object_generation.builder import generate_ckos
from compiler_engine.paper_import.schema import PaperImport
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.pipeline.stage import PipelineStage, StageResult


class CkoGenerationStage(PipelineStage):
    stage_name = "canonical_knowledge_object_generation"

    def validate_inputs(self, context: CompilerContext) -> None:
        if not context.registry.all(PaperImport):
            raise CompilerError(
                "No PaperImport artifacts registered; run paper_import before "
                "canonical_knowledge_object_generation"
            )
        if not context.registry.all(RelationshipGraph):
            raise CompilerError(
                "No RelationshipGraph artifacts registered; run relationship_resolution "
                "before canonical_knowledge_object_generation"
            )
        if not context.registry.all(EducationalAnalysis):
            raise CompilerError(
                "No EducationalAnalysis artifacts registered; run educational_analysis "
                "before canonical_knowledge_object_generation"
            )

    def execute(self, context: CompilerContext) -> StageResult:
        ckos = generate_ckos(context)

        artifact_ids = tuple(
            context.registry.register(cko, artifact_id=cko.cko_id) for cko in ckos
        )

        merged_count = sum(1 for cko in ckos if len(cko.lineage.occurrences) > 1)
        warnings: tuple[str, ...] = ()
        if merged_count:
            warnings = (
                f"{merged_count} CKO(s) merged occurrences from more than one paper.",
            )

        return StageResult.ok(self.stage_name, artifact_ids=artifact_ids, warnings=warnings)
