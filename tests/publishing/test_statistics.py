from datetime import datetime, timezone

from compiler_engine.core.config import CompilerConfig
from compiler_engine.domain.cko import CKO, CkoEvolution, CkoLineage, CkoOccurrence, CkoRelationships, CkoStatus
from compiler_engine.domain.educational_analysis import EducationalAnalysis
from compiler_engine.domain.relationship_graph import RelationshipGraph, RelationshipNode
from compiler_engine.domain.validation_report import ValidationIssue, ValidationReport, ValidationSeverity
from compiler_engine.paper_import.schema import (
    PaperImport,
    PaperMetadata,
    PaperSection,
    RawClassification,
    RawContent,
    RawQuestion,
    RawQuestionIdentity,
    RawRelationships,
    TextBlock,
)
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.publishing.statistics import compute_statistics


def _metadata() -> PaperMetadata:
    return PaperMetadata(
        board="CBSE", conducting_body="X", region="Delhi", examination="Exam",
        academic_session="2025-26", class_name="XII", subject="COMPUTER SCIENCE",
        subject_code="083", duration="3 HOURS", maximum_marks=10, set="SET A",
        total_questions=1, total_sections=1,
    )


def _question(question_id: str) -> RawQuestion:
    return RawQuestion(
        identity=RawQuestionIdentity(question_id=question_id, original_question_number="1", section_id="sec_a"),
        classification=RawClassification(
            chapter="ch_x", topic="top_x", concept="con_x", keywords=("kw",),
            difficulty="diff_easy", bloom_level="bloom_remember", question_type="qt_mcq",
        ),
        content=RawContent(blocks=(TextBlock(block_type="text", value=question_id),)),
        options=None,
        relationships=RawRelationships(),
        assessment=None,
    )


def _paper(paper_id: str, *question_ids: str) -> PaperImport:
    return PaperImport(
        schema_version="1.0", paper_id=paper_id, paper_metadata=_metadata(),
        sections=(PaperSection(section_id="sec_a", title="A", marks_per_question=1, question_range="1-1"),),
        questions=tuple(_question(qid) for qid in question_ids),
    )


def _cko(cko_id: str, num_occurrences: int) -> CKO:
    occurrence = CkoOccurrence(
        paper_id="p1", examination="Exam", session="2025-26", region="Delhi",
        original_question_number="1", allocated_marks=1,
    )
    return CKO(
        cko_id=cko_id, version=1, checksum=cko_id, created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc), status=CkoStatus.UNDER_REVIEW,
        classification=EducationalAnalysis(question_id="Q1", subject="CS", topic="top_x"),
        content=RawContent(blocks=(TextBlock(block_type="text", value="x"),)), options=None,
        relationships=CkoRelationships(),
        lineage=CkoLineage(occurrences=(occurrence,) * num_occurrences),
        evolution=CkoEvolution(),
    )


def _context() -> CompilerContext:
    config = CompilerConfig(import_workspace="/tmp/x", assets_folder="/tmp/y", output_folder="/tmp/z")
    return CompilerContext.create(config)


def _register_paper(context: CompilerContext, paper: PaperImport) -> None:
    # Mirrors PaperImportStage's actual registration convention: the paper AND each of
    # its questions are registered as separate artifacts.
    context.registry.register(paper, artifact_id=paper.paper_id)
    for question in paper.questions:
        context.registry.register(
            question, artifact_id=f"{paper.paper_id}::{question.identity.question_id}"
        )


def test_counts_papers_questions_and_ckos():
    context = _context()
    _register_paper(context, _paper("p1", "Q1", "Q2"))
    context.registry.register(_cko("cko_a", 1), artifact_id="cko_a")
    context.registry.register(_cko("cko_b", 1), artifact_id="cko_b")

    stats = compute_statistics(context)

    assert stats.papers_processed == 1
    assert stats.questions_imported == 2
    assert stats.ckos_created == 2
    assert stats.duplicate_questions_merged == 0


def test_duplicate_questions_merged_is_questions_minus_ckos():
    context = _context()
    _register_paper(context, _paper("p1", "Q1", "Q2", "Q3"))
    # 3 questions merged into 1 CKO (2 were duplicates of it).
    context.registry.register(_cko("cko_a", 3), artifact_id="cko_a")

    stats = compute_statistics(context)

    assert stats.questions_imported == 3
    assert stats.ckos_created == 1
    assert stats.duplicate_questions_merged == 2


def test_counts_orphan_relationship_references():
    context = _context()
    graph = RelationshipGraph(
        paper_id="p1",
        nodes=(
            RelationshipNode(question_id="Q1", is_resolved=True),
            RelationshipNode(question_id="Q_ghost", is_resolved=False),
        ),
        edges=(),
    )
    context.registry.register(graph, artifact_id="p1")

    stats = compute_statistics(context)

    assert stats.orphan_relationships_skipped == 1


def test_counts_validation_warnings_and_errors_separately():
    context = _context()
    report = ValidationReport(
        target_id="p1",
        is_valid=False,
        issues=(
            ValidationIssue(code="A", message="a", severity=ValidationSeverity.ERROR),
            ValidationIssue(code="B", message="b", severity=ValidationSeverity.WARNING),
            ValidationIssue(code="C", message="c", severity=ValidationSeverity.WARNING),
            ValidationIssue(code="D", message="d", severity=ValidationSeverity.INFO),
        ),
        generated_at=datetime.now(timezone.utc),
    )
    context.registry.register(report, artifact_id="p1")

    stats = compute_statistics(context)

    assert stats.validation_errors == 1
    assert stats.validation_warnings == 2


def test_empty_registry_produces_all_zero_statistics():
    stats = compute_statistics(_context())
    assert stats.papers_processed == 0
    assert stats.questions_imported == 0
    assert stats.ckos_created == 0
    assert stats.duplicate_questions_merged == 0
    assert stats.orphan_relationships_skipped == 0
    assert stats.validation_warnings == 0
    assert stats.validation_errors == 0
