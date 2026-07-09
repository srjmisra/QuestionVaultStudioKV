"""Answer IR: the answer half of a question, kept separate from Question IR so a
question's stem/options and its answer key can be validated and versioned independently.
"""

from __future__ import annotations

from pydantic import Field

from compiler_engine.core.base_model import CompilerBaseModel
from compiler_engine.core.schema_versions import CURRENT_SCHEMA_VERSIONS


class AnswerOption(CompilerBaseModel):
    option_id: str
    text: str
    is_correct: bool


class AnswerIR(CompilerBaseModel):
    schema_version: str = CURRENT_SCHEMA_VERSIONS["answer_ir"]
    answer_type: str = Field(
        description=(
            'Open string, e.g. "single_choice", "multi_choice", "descriptive", "numeric", '
            '"code". Not an enum yet: the set of supported answer types is a classification-'
            "stage decision, not a Sprint 1 one."
        )
    )
    options: tuple[AnswerOption, ...] = ()
    descriptive_answer: str | None = None
    explanation: str | None = None
    marks: float | None = Field(default=None, ge=0)
