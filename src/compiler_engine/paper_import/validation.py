"""Business-rule validation for an already-parsed PaperImport.

Structural validity (required fields, well-formed blocks, correct types) is handled by
pydantic when the JSON is parsed into PaperImport — a payload that fails there can't be
represented as a PaperImport at all, so it never reaches this module. What's checked
here are rules that need the *whole* parsed paper to evaluate: cross-references between
questions and sections, relationships between questions, duplicate IDs, and whether this
importer supports the paper's declared schema_version.
"""

from __future__ import annotations

from compiler_engine.domain.validation_report import ValidationIssue, ValidationSeverity
from compiler_engine.paper_import.schema import SUPPORTED_SCHEMA_VERSIONS, PaperImport


def validate_paper(paper: PaperImport) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []

    issues.extend(_check_schema_version(paper))
    issues.extend(_check_duplicate_question_ids(paper))
    issues.extend(_check_section_references(paper))
    issues.extend(_check_relationship_integrity(paper))

    return tuple(issues)


def _check_schema_version(paper: PaperImport) -> list[ValidationIssue]:
    if paper.schema_version in SUPPORTED_SCHEMA_VERSIONS:
        return []
    return [
        ValidationIssue(
            code="UNSUPPORTED_SCHEMA_VERSION",
            message=(
                f"schema_version {paper.schema_version!r} is not supported by this "
                f"importer (supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)})"
            ),
            severity=ValidationSeverity.ERROR,
            field_path="schema_version",
        )
    ]


def _check_duplicate_question_ids(paper: PaperImport) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen: set[str] = set()
    for index, question in enumerate(paper.questions):
        question_id = question.identity.question_id
        if question_id in seen:
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_QUESTION_ID",
                    message=f"question_id {question_id!r} appears more than once",
                    severity=ValidationSeverity.ERROR,
                    field_path=f"questions[{index}].identity.question_id",
                )
            )
        seen.add(question_id)
    return issues


def _check_section_references(paper: PaperImport) -> list[ValidationIssue]:
    known_section_ids = {section.section_id for section in paper.sections}
    issues: list[ValidationIssue] = []
    for index, question in enumerate(paper.questions):
        section_id = question.identity.section_id
        if section_id not in known_section_ids:
            issues.append(
                ValidationIssue(
                    code="UNKNOWN_SECTION_REFERENCE",
                    message=(
                        f"question {question.identity.question_id!r} references unknown "
                        f"section_id {section_id!r}"
                    ),
                    severity=ValidationSeverity.ERROR,
                    field_path=f"questions[{index}].identity.section_id",
                )
            )
    return issues


def _check_relationship_integrity(paper: PaperImport) -> list[ValidationIssue]:
    known_question_ids = {question.identity.question_id for question in paper.questions}
    issues: list[ValidationIssue] = []

    for index, question in enumerate(paper.questions):
        question_id = question.identity.question_id
        relationships = question.relationships

        referenced: list[tuple[str, str]] = []
        if relationships.parent_id is not None:
            referenced.append(("parent_id", relationships.parent_id))
        referenced.extend(("child_ids", child_id) for child_id in relationships.child_ids)
        referenced.extend(
            ("sibling_or_ids", sibling_id) for sibling_id in relationships.sibling_or_ids
        )

        for field_name, referenced_id in referenced:
            if referenced_id not in known_question_ids:
                issues.append(
                    ValidationIssue(
                        code="DANGLING_RELATIONSHIP_REFERENCE",
                        message=(
                            f"question {question_id!r} has {field_name}={referenced_id!r}, "
                            "which does not match any question_id in this paper"
                        ),
                        severity=ValidationSeverity.ERROR,
                        field_path=f"questions[{index}].relationships.{field_name}",
                    )
                )

    return issues
