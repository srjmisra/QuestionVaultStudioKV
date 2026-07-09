"""Verifies paper.json's raw `classification` against the canonical reference
taxonomies, and normalizes it into EducationalAnalysis objects.

Two independent, deliberately separate operations:

- `build_educational_analysis` is a pure, mechanical field mapping. It never looks at
  the reference taxonomies and never fails — every question gets an EducationalAnalysis,
  even one built from classification that verification would reject. It transcribes
  what Gemini said; it does not judge it. `difficulty`/`bloom_level` fall back to `None`
  when the raw string doesn't match a known value (not fabricated, not guessed — the
  corresponding ValidationIssue from `detect_issues` explains why).
- `detect_issues` is the actual verification: existence, hierarchy, validity, and
  keyword/metadata hygiene checks. It only ever reports; it never repairs anything it
  finds wrong, and it never touches question text.

Field mapping (paper.json `classification` -> EducationalAnalysis, Sprint 1's model,
used unmodified): `subject` <- paper_metadata.subject (a different axis entirely — the
whole paper's subject, e.g. "COMPUTER SCIENCE" — not part of chapter/topic/concept at
all); `topic` <- classification.topic (name matches exactly); `subtopic` <-
classification.concept (concept is finer-grained than topic, the closest fit); nothing
is dropped even though `chapter` has no exact-matching field, because `taxonomy_path`
holds the complete, faithful (chapter, topic, concept) tuple.

"Every chapter belongs to the declared unit" (paper.json has no per-question `unit`
field to check against) is treated as already covered by chapter-existence: a chapter
resolving in the curriculum index at all necessarily has a unit ancestor, because that's
how the tree is built.

"Reject duplicate concept IDs within the same question" doesn't apply literally —
`classification.concept` is a single string, not an array, in the frozen v1.0 schema.
This is instead checked across the sub-questions sharing one `original_question_number`
(e.g. Q23_i / Q23_ii): two sub-parts of the same original question declaring the
identical concept is a plausible classification-quality signal, reported as a WARNING
since it isn't necessarily wrong.
"""

from __future__ import annotations

from collections import defaultdict

from compiler_engine.domain.educational_analysis import BloomLevel, DifficultyLevel, EducationalAnalysis
from compiler_engine.domain.validation_report import ValidationIssue, ValidationSeverity
from compiler_engine.educational_analysis.reference import CurriculumIndex
from compiler_engine.paper_import.schema import PaperImport, RawQuestion

_DIFFICULTY_BY_RAW: dict[str, DifficultyLevel] = {
    "diff_easy": DifficultyLevel.EASY,
    "diff_medium": DifficultyLevel.MEDIUM,
    "diff_hard": DifficultyLevel.HARD,
}

_BLOOM_BY_RAW: dict[str, BloomLevel] = {
    "bloom_remember": BloomLevel.REMEMBER,
    "bloom_understand": BloomLevel.UNDERSTAND,
    "bloom_apply": BloomLevel.APPLY,
    "bloom_analyze": BloomLevel.ANALYZE,
    "bloom_evaluate": BloomLevel.EVALUATE,
    "bloom_create": BloomLevel.CREATE,
}


def build_educational_analysis(paper: PaperImport) -> tuple[EducationalAnalysis, ...]:
    results = []
    for question in paper.questions:
        classification = question.classification
        results.append(
            EducationalAnalysis(
                question_id=question.identity.question_id,
                subject=paper.paper_metadata.subject,
                topic=classification.topic,
                subtopic=classification.concept,
                difficulty=_DIFFICULTY_BY_RAW.get(classification.difficulty),
                bloom_level=_BLOOM_BY_RAW.get(classification.bloom_level),
                keywords=classification.keywords,
                taxonomy_path=(classification.chapter, classification.topic, classification.concept),
            )
        )
    return tuple(results)


def detect_issues(
    paper: PaperImport,
    curriculum_index: CurriculumIndex,
    valid_question_type_ids: frozenset[str],
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    for question in paper.questions:
        issues.extend(_check_taxonomy_ids(question, curriculum_index, valid_question_type_ids))
        issues.extend(_check_bloom_and_difficulty(question))
        issues.extend(_check_hierarchy(question, curriculum_index))
        issues.extend(_check_required_metadata(question))
        issues.extend(_check_keywords(question))
    issues.extend(_check_duplicate_concepts_within_question_group(paper))
    return tuple(issues)


def _field_path(question: RawQuestion, field_name: str) -> str:
    return f"questions[{question.identity.question_id}].classification.{field_name}"


def _check_taxonomy_ids(
    question: RawQuestion,
    curriculum_index: CurriculumIndex,
    valid_question_type_ids: frozenset[str],
) -> list[ValidationIssue]:
    classification = question.classification
    checks = (
        ("chapter", classification.chapter, curriculum_index.chapter_ids),
        ("topic", classification.topic, curriculum_index.topic_ids),
        ("concept", classification.concept, curriculum_index.concept_ids),
        ("question_type", classification.question_type, valid_question_type_ids),
    )
    issues = []
    for field_name, value, known_ids in checks:
        if value not in known_ids:
            issues.append(
                ValidationIssue(
                    code="UNKNOWN_TAXONOMY_ID",
                    message=(
                        f"question {question.identity.question_id!r} has {field_name}="
                        f"{value!r}, which does not exist in the canonical taxonomy"
                    ),
                    severity=ValidationSeverity.ERROR,
                    field_path=_field_path(question, field_name),
                )
            )
    return issues


def _check_bloom_and_difficulty(question: RawQuestion) -> list[ValidationIssue]:
    classification = question.classification
    issues = []
    if classification.difficulty not in _DIFFICULTY_BY_RAW:
        issues.append(
            ValidationIssue(
                code="INVALID_DIFFICULTY_TIER",
                message=(
                    f"question {question.identity.question_id!r} has difficulty="
                    f"{classification.difficulty!r}, which is not a recognized tier"
                ),
                severity=ValidationSeverity.ERROR,
                field_path=_field_path(question, "difficulty"),
            )
        )
    if classification.bloom_level not in _BLOOM_BY_RAW:
        issues.append(
            ValidationIssue(
                code="INVALID_BLOOM_LEVEL",
                message=(
                    f"question {question.identity.question_id!r} has bloom_level="
                    f"{classification.bloom_level!r}, which is not a recognized level"
                ),
                severity=ValidationSeverity.ERROR,
                field_path=_field_path(question, "bloom_level"),
            )
        )
    return issues


def _check_hierarchy(question: RawQuestion, curriculum_index: CurriculumIndex) -> list[ValidationIssue]:
    classification = question.classification
    issues = []

    if classification.topic in curriculum_index.topic_ids:
        expected_chapter = curriculum_index.chapter_of_topic.get(classification.topic)
        if expected_chapter is not None and expected_chapter != classification.chapter:
            issues.append(
                ValidationIssue(
                    code="HIERARCHY_MISMATCH",
                    message=(
                        f"question {question.identity.question_id!r} declares topic="
                        f"{classification.topic!r} under chapter={classification.chapter!r}, "
                        f"but the canonical taxonomy places that topic under "
                        f"{expected_chapter!r}"
                    ),
                    severity=ValidationSeverity.ERROR,
                    field_path=_field_path(question, "topic"),
                )
            )

    if classification.concept in curriculum_index.concept_ids:
        expected_topic = curriculum_index.topic_of_concept.get(classification.concept)
        if expected_topic is not None and expected_topic != classification.topic:
            issues.append(
                ValidationIssue(
                    code="HIERARCHY_MISMATCH",
                    message=(
                        f"question {question.identity.question_id!r} declares concept="
                        f"{classification.concept!r} under topic={classification.topic!r}, "
                        f"but the canonical taxonomy places that concept under "
                        f"{expected_topic!r}"
                    ),
                    severity=ValidationSeverity.ERROR,
                    field_path=_field_path(question, "concept"),
                )
            )

    return issues


def _check_required_metadata(question: RawQuestion) -> list[ValidationIssue]:
    classification = question.classification
    required_fields = (
        "chapter",
        "topic",
        "concept",
        "question_type",
        "difficulty",
        "bloom_level",
    )
    issues = []
    for field_name in required_fields:
        value = getattr(classification, field_name)
        if not value.strip():
            issues.append(
                ValidationIssue(
                    code="MISSING_EDUCATIONAL_METADATA",
                    message=(
                        f"question {question.identity.question_id!r} has an empty "
                        f"classification.{field_name}"
                    ),
                    severity=ValidationSeverity.ERROR,
                    field_path=_field_path(question, field_name),
                )
            )
    return issues


def _check_keywords(question: RawQuestion) -> list[ValidationIssue]:
    keywords = question.classification.keywords
    issues = []

    if not keywords:
        issues.append(
            ValidationIssue(
                code="INVALID_KEYWORDS",
                message=f"question {question.identity.question_id!r} has no keywords",
                severity=ValidationSeverity.WARNING,
                field_path=_field_path(question, "keywords"),
            )
        )

    seen: set[str] = set()
    for keyword in keywords:
        if not keyword.strip():
            issues.append(
                ValidationIssue(
                    code="INVALID_KEYWORDS",
                    message=f"question {question.identity.question_id!r} has a blank keyword",
                    severity=ValidationSeverity.WARNING,
                    field_path=_field_path(question, "keywords"),
                )
            )
        elif keyword in seen:
            issues.append(
                ValidationIssue(
                    code="INVALID_KEYWORDS",
                    message=(
                        f"question {question.identity.question_id!r} has duplicate "
                        f"keyword {keyword!r}"
                    ),
                    severity=ValidationSeverity.WARNING,
                    field_path=_field_path(question, "keywords"),
                )
            )
        seen.add(keyword)

    return issues


def _check_duplicate_concepts_within_question_group(paper: PaperImport) -> list[ValidationIssue]:
    groups: dict[str, list[RawQuestion]] = defaultdict(list)
    for question in paper.questions:
        groups[question.identity.original_question_number].append(question)

    issues: list[ValidationIssue] = []
    for members in groups.values():
        if len(members) < 2:
            continue
        seen_by_concept: dict[str, str] = {}
        for question in members:
            concept = question.classification.concept
            question_id = question.identity.question_id
            if concept in seen_by_concept:
                issues.append(
                    ValidationIssue(
                        code="DUPLICATE_CONCEPT_IN_QUESTION_GROUP",
                        message=(
                            f"question {question_id!r} and {seen_by_concept[concept]!r} "
                            f"(both part of original question "
                            f"{question.identity.original_question_number!r}) declare "
                            f"the same concept {concept!r}"
                        ),
                        severity=ValidationSeverity.WARNING,
                        field_path=_field_path(question, "concept"),
                    )
                )
            else:
                seen_by_concept[concept] = question_id

    return issues
