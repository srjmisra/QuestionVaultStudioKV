"""Wire-format models for paper.json Version 1.0 — the frozen, external contract Gemini
produces. These mirror the file field-for-field and deliberately do NOT reuse the
compiler's own canonical IR models (QuestionIR, EducationalAnalysis, ...): a raw
`classification.chapter/topic/concept` is Gemini's candidate guess, not yet resolved
against the canonical Taxonomy, and conflating the two would let unvalidated wire data
masquerade as a trusted internal artifact. Educational Analysis (the resolution step) is
explicitly out of scope for this sprint.

`assessment` is modeled as an untyped, optional dict: every question in the only
production file seen so far has it set to null, so its populated shape has never been
observed. Accepting-and-passing-through rather than validating it is deliberate, not an
oversight.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import Field

from compiler_engine.core.base_model import CompilerBaseModel

SUPPORTED_SCHEMA_VERSIONS = frozenset({"1.0"})


class TextBlock(CompilerBaseModel):
    block_type: Literal["text"]
    value: str


class CodeBlock(CompilerBaseModel):
    block_type: Literal["code"]
    language: str
    value: str


class TableBlock(CompilerBaseModel):
    block_type: Literal["table"]
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


ContentBlock = Annotated[Union[TextBlock, CodeBlock, TableBlock], Field(discriminator="block_type")]


class RawContent(CompilerBaseModel):
    blocks: tuple[ContentBlock, ...]


class RawOption(CompilerBaseModel):
    option_id: str
    display_order: int
    blocks: tuple[ContentBlock, ...]


class RawQuestionIdentity(CompilerBaseModel):
    question_id: str = Field(min_length=1)
    original_question_number: str
    section_id: str


class RawClassification(CompilerBaseModel):
    chapter: str
    topic: str
    concept: str
    keywords: tuple[str, ...]
    difficulty: str
    bloom_level: str
    question_type: str


class RawRelationships(CompilerBaseModel):
    parent_id: str | None = None
    child_ids: tuple[str, ...] = ()
    sibling_or_ids: tuple[str, ...] = ()


class RawQuestion(CompilerBaseModel):
    identity: RawQuestionIdentity
    classification: RawClassification
    content: RawContent
    options: tuple[RawOption, ...] | None = None
    relationships: RawRelationships
    assessment: dict[str, Any] | None = None


class PaperSection(CompilerBaseModel):
    section_id: str = Field(min_length=1)
    title: str
    marks_per_question: int = Field(ge=0)
    question_range: str


class PaperMetadata(CompilerBaseModel):
    model_config = CompilerBaseModel.model_config | {"populate_by_name": True}

    board: str
    conducting_body: str
    region: str
    examination: str
    academic_session: str
    class_name: str = Field(alias="class")
    subject: str
    subject_code: str
    duration: str
    maximum_marks: int = Field(ge=0)
    set: str
    total_questions: int = Field(ge=0)
    total_sections: int = Field(ge=0)


class PaperImport(CompilerBaseModel):
    schema_version: str
    paper_id: str = Field(min_length=1)
    paper_metadata: PaperMetadata
    sections: tuple[PaperSection, ...]
    questions: tuple[RawQuestion, ...]
