"""Builds CKOs from already-validated PaperImport / RelationshipGraph /
EducationalAnalysis artifacts already in the registry. Never reads paper.json directly,
never reclassifies, never re-derives relationships — it only computes each question's
content checksum, groups identical-content questions into one CKO each, and translates
paper-scoped question_ids into checksum-derived cko_ids.

Processing order is fixed (papers sorted by paper_id, questions in their original
paper.json array order) so that generation is fully deterministic and reproducible —
running it twice on the same registry contents produces byte-identical CKOs.

When two or more questions share a checksum (the same question occurring in more than
one paper), classification and relationships are taken from the *first* occurrence in
that deterministic order; later occurrences only contribute a lineage entry. This is a
simple, explicit tie-break, not a conflict-resolution system — Sprint 6 doesn't ask for
one, so none is built.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timezone

from compiler_engine.domain.cko import (
    CKO,
    CkoEvolution,
    CkoLineage,
    CkoOccurrence,
    CkoRelationships,
    CkoStatus,
)
from compiler_engine.domain.educational_analysis import EducationalAnalysis
from compiler_engine.domain.relationship_graph import RelationshipGraph
from compiler_engine.canonical_knowledge_object_generation.checksum import compute_checksum
from compiler_engine.paper_import.schema import PaperImport, RawQuestion
from compiler_engine.pipeline.context import CompilerContext

_QuestionRecord = tuple[PaperImport, RawQuestion, EducationalAnalysis]


def generate_ckos(context: CompilerContext) -> tuple[CKO, ...]:
    now = datetime.now(timezone.utc)
    papers = sorted(context.registry.all(PaperImport), key=lambda paper: paper.paper_id)

    checksum_by_question_key: dict[tuple[str, str], str] = {}
    groups: dict[str, list[_QuestionRecord]] = defaultdict(list)

    for paper in papers:
        for question in paper.questions:
            question_id = question.identity.question_id
            analysis = context.registry.get(
                EducationalAnalysis, f"{paper.paper_id}::{question_id}"
            )
            checksum = compute_checksum(question.content, question.options)
            checksum_by_question_key[(paper.paper_id, question_id)] = checksum
            groups[checksum].append((paper, question, analysis))

    def cko_id_for(paper_id: str, question_id: str) -> str | None:
        checksum = checksum_by_question_key.get((paper_id, question_id))
        return f"cko_{checksum}" if checksum else None

    ckos = []
    for checksum, members in groups.items():
        first_paper, first_question, first_analysis = members[0]
        cko_id = f"cko_{checksum}"

        occurrences = tuple(
            CkoOccurrence(
                paper_id=paper.paper_id,
                examination=paper.paper_metadata.examination,
                session=paper.paper_metadata.academic_session,
                region=paper.paper_metadata.region,
                original_question_number=question.identity.original_question_number,
                allocated_marks=_allocated_marks(paper, question),
            )
            for paper, question, _ in members
        )

        ckos.append(
            CKO(
                cko_id=cko_id,
                # Version tracks editorial evolution of the canonical content, not
                # lineage — occurrence count belongs to `lineage`, not `version`. This
                # stage never edits content, so every CKO it produces starts at 1.
                version=1,
                checksum=checksum,
                created_at=now,
                updated_at=now,
                status=CkoStatus.UNDER_REVIEW,
                classification=first_analysis,
                content=first_question.content,
                options=first_question.options,
                relationships=_resolve_relationships(context, first_paper, first_question, cko_id_for),
                lineage=CkoLineage(occurrences=occurrences),
                evolution=CkoEvolution(),
            )
        )

    return tuple(sorted(ckos, key=lambda cko: cko.cko_id))


def _allocated_marks(paper: PaperImport, question: RawQuestion) -> int | None:
    for section in paper.sections:
        if section.section_id == question.identity.section_id:
            return section.marks_per_question
    return None


def _resolve_relationships(
    context: CompilerContext,
    paper: PaperImport,
    question: RawQuestion,
    cko_id_for: Callable[[str, str], str | None],
) -> CkoRelationships:
    graph = context.registry.get(RelationshipGraph, paper.paper_id)
    question_id = question.identity.question_id
    node = next((n for n in graph.nodes if n.question_id == question_id), None)
    if node is None:
        return CkoRelationships()

    parent_cko_id = cko_id_for(paper.paper_id, node.parent_id) if node.parent_id else None

    child_cko_ids = tuple(
        cko_id
        for cko_id in (cko_id_for(paper.paper_id, child_id) for child_id in node.child_ids)
        if cko_id is not None
    )

    sibling_or_cko_ids: tuple[str, ...] = ()
    if node.or_choice_group_id is not None:
        sibling_question_ids = [
            other.question_id
            for other in graph.nodes
            if other.or_choice_group_id == node.or_choice_group_id
            and other.question_id != question_id
        ]
        sibling_or_cko_ids = tuple(
            cko_id
            for cko_id in (cko_id_for(paper.paper_id, sid) for sid in sibling_question_ids)
            if cko_id is not None
        )

    return CkoRelationships(
        parent_cko_id=parent_cko_id,
        child_cko_ids=child_cko_ids,
        sibling_or_cko_ids=sibling_or_cko_ids,
    )
