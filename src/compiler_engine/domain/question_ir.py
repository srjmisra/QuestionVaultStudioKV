"""Question IR: one extracted question, independent of subject/topic classification."""

from __future__ import annotations

from pydantic import Field

from compiler_engine.core.base_model import CompilerBaseModel
from compiler_engine.core.schema_versions import CURRENT_SCHEMA_VERSIONS
from compiler_engine.domain.answer_ir import AnswerIR


class QuestionIR(CompilerBaseModel):
    schema_version: str = CURRENT_SCHEMA_VERSIONS["question_ir"]
    question_id: str
    source_document_id: str
    question_number: str | None = None
    stem: str
    question_type: str = Field(
        description=(
            'Open string, e.g. "mcq", "subjective", "assertion_reason", "output_based", '
            '"sql", "programming". Not an enum yet: fixing the full set of question types is '
            "an educational-classification decision, not a Sprint 1 one."
        )
    )
    marks: float | None = Field(default=None, ge=0)
    answer: AnswerIR | None = None
    sub_questions: tuple["QuestionIR", ...] = ()
    source_ast_node_ids: tuple[str, ...] = ()
