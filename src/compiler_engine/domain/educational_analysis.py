"""Educational Analysis: subject/topic classification and pedagogical metadata for a
question, kept separate from Question IR so re-classification never touches the
extracted question content.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from compiler_engine.core.base_model import CompilerBaseModel
from compiler_engine.core.schema_versions import CURRENT_SCHEMA_VERSIONS


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class BloomLevel(str, Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class EducationalAnalysis(CompilerBaseModel):
    schema_version: str = CURRENT_SCHEMA_VERSIONS["educational_analysis"]
    question_id: str
    subject: str
    topic: str
    subtopic: str | None = None
    difficulty: DifficultyLevel | None = None
    bloom_level: BloomLevel | None = None
    keywords: tuple[str, ...] = ()
    estimated_time_seconds: int | None = Field(default=None, ge=0)
    taxonomy_path: tuple[str, ...] = ()
