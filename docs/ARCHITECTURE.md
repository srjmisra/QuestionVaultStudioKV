# QuestionVault Studio — Architecture

Status: finalized, revised after the Gemini JSON Import architecture change (see
"Architecture history" below). This document records the architecture as decided;
it is not a design proposal.

## Product context

KV Coders is an existing production educational platform (PHP 8, MySQL, HTML/CSS/JS,
Bluehost shared hosting, main application at `/public_html/examiner/`). It already has
student authentication, teacher/admin dashboards, an LMS, MCQ/SQL/Output-question practice,
AI evaluation, video learning, test arena, and progress tracking.

QuestionVault Studio is a new module inside that existing platform: the question import
and knowledge management feature. It is not a standalone product and not a separate
website — it extends KV Coders.

QuestionVault Studio is **not a PDF parser**. It is a Knowledge Import & Publishing
Engine: it takes an already-structured JSON artifact and turns it into validated,
publishable knowledge objects. It has two independent parts, and this repository
contains only one of them.

## Pipeline

```
Original PDF
     │
     ▼
Gemini Advanced (outside this repository)
     │
     ▼
paper.json  ← the ONLY input this engine ever reads
     │
     ▼
QuestionVault Studio (this repository)
     │  Validation
     │  Relationship Resolution
     │  Canonical Knowledge Object Generation
     │  Database Export  (produces publishable JSON artifacts — no MySQL, ever)
     ▼
KV Coders Website (PHP Admin Module: upload, review, publish, MySQL import, search index)
```

The Python engine never reads the original PDF. Gemini Advanced does all PDF/OCR
processing, outside this repository, and hands over `paper.json`.

## Part A — Python Compilation Engine (this repository)

Runs locally (MacBook Air M1) during content creation. Students never interact with it.
Reads `paper.json` and, through a pipeline of discrete stages, produces validated
publishable JSON artifacts. Nothing here talks to MySQL, to Bluehost, or to the live
website — "Database Export" means producing artifacts the PHP side can import, not
connecting to a database.

Stages (folders under `src/compiler_engine/`):
- `paper_import/` — **implemented (Sprint 3).** Loads `paper.json`, validates it against
  `paper.json` Version 1.0 (frozen — see below), produces a `ValidationReport`, and
  registers the parsed `PaperImport` and every `RawQuestion` in the `ArtifactRegistry`.
  A stage-level success means the file was loaded and validated, not that the paper is
  free of problems — a paper with validation errors still succeeds the stage; the
  `ValidationReport.is_valid` flag and its `issues` are what carry the actual verdict.
- `educational_analysis/` — reserved; exact position in the pipeline relative to
  Relationship Resolution/CKO Generation is still open (see "Open questions" below)
- `relationship_resolution/` — reserved
- `canonical_knowledge_object_generation/` — reserved
- `database_export/` — reserved; produces publishable JSON only
- `validation/` — reserved and still empty; `paper_import/`'s business-rule validation
  (`paper_import/validation.py`) turned out to be tightly coupled to the paper.json wire
  shape and lives inside `paper_import/` rather than here — this folder remains for
  validation logic shared across multiple future stages, if that need arises

### paper.json Version 1.0 (frozen)

Frozen by explicit decision after reviewing the first real Gemini-generated file. No
further schema changes without a major version bump. Modeled field-for-field in
`paper_import/schema.py` as `PaperImport` (top level: `schema_version`, `paper_id`,
`paper_metadata`, `sections`, `questions`) — deliberately kept separate from the
compiler's own canonical IR (`QuestionIR`, `EducationalAnalysis`, ...), since a raw
`classification.chapter/topic/concept` is Gemini's candidate guess, not yet resolved
against the canonical Taxonomy.

Known, accepted imperfections in the frozen v1.0 shape (not fixed, because fixing them
would mean changing already-frozen structure or inventing data that was never extracted):
- No per-question marks field — marks are only known at the section level
  (`marks_per_question`), so sub-parts of a multi-part question have no individual
  weight.
- Three different, inconsistent conventions for encoding "this is part of a bigger
  numbered question" (full parent/child linking, a dangling parent reference with no
  parent entry, or no linking at all — grouped only by a shared
  `original_question_number`). `paper_import/validation.py` catches dangling references
  as a `DANGLING_RELATIONSHIP_REFERENCE` validation issue but does not repair them.
- `assessment` is `null` on every question in the only production file seen so far; its
  populated shape has never been observed, so it's modeled as an untyped optional dict
  rather than a real schema.
- No field describes how non-text assets (diagrams, images) would be referenced from a
  content block — unobserved in the only file seen so far (it has none).

Deprecated: `compiler_engine.domain.document_ast` (`DocumentAST`, `ASTNode`,
`ASTNodeType`, `BoundingBox`) modeled a PDF layout tree the engine would have produced
itself. Nothing produces or consumes it now. Kept, not deleted, in case Gemini's
`paper.json` still carries structural information (page numbers, question boundaries,
asset references, logical blocks) worth preserving in a similar shape — that will be
decided after the real schema is reviewed.

### Import workspace layout (target shape, not yet implemented)

```
imports/
    CBSE_2026/
        original.pdf      ← human reference only; the compiler never reads this
        paper.json         ← the only file the compiler reads
        validation.json
        review.json
        assets/
```

This is a per-paper layout (one subfolder per imported paper), which differs from the
single flat `import_workspace`/`assets_folder`/`output_folder` that `WorkspaceManager`
(Sprint 2) currently implements. `WorkspaceManager` has not been updated to match this
yet — that will happen as part of building `paper_import/` in Sprint 3, once the real
`paper.json` is available.

## Part B — KV Coders Admin Module (separate repository: KV Coders, PHP/MySQL, already exists)

Runs on Bluehost as another admin feature inside the existing KV Coders website — not a
separate application. Consumes the publishable JSON artifacts produced by Part A and:
- Uploads/imports them
- Reviews imported papers, edits metadata, merges duplicate questions, maintains occurrences
- Publishes questions, manages taxonomy, manages assets
- Imports into MySQL and rebuilds the search index
- Monitors validation reports

QuestionVault Studio (Part A) never connects to MySQL, never talks to Bluehost, and
never talks to the website directly. Its responsibility ends at producing validated,
publishable artifacts.

## Downstream effect (no new work required in either repo)

Once questions are published via Part B, the existing KV Coders Student Dashboard gains
features such as topic-wise/keyword search, previous-year/programming/SQL/networking
question sets, MCQ practice, assertion & reason questions, output questions, worksheet and
mock paper generation, related questions, question history, and exam trend analysis. This
is existing student-facing surface being fed new data — not new subsystems.

## Repository boundaries

- **Repository 1 — QuestionVaultStudio (this repo):** Python Compilation Engine only.
- **Repository 2 — KV Coders (existing, separate repo):** the PHP/MySQL website, including
  the Admin Module (Part B) and all student-facing features.

## Open questions (tracked here until resolved)

- **`educational_analysis/`'s exact position** in the Validation → Relationship
  Resolution → CKO Generation → Database Export sequence is not yet confirmed — it may
  be produced by Gemini directly inside `paper.json`, or remain a distinct stage.
- **`WorkspaceManager`'s layout** will need to change from a single flat
  workspace/assets/output model to the per-paper `imports/<paper_id>/` layout shown
  above; not yet implemented — Sprint 3 reads `paper.json` from a path passed in
  directly (`--paper`), not from that per-paper folder convention.
- **Asset referencing.** How a content block would point at an image/diagram file is
  still unobserved — no production `paper.json` seen so far contains one.
- **`assessment`'s real shape.** Still never seen populated; `paper_import` accepts it
  as an untyped dict rather than validating it.

## Architecture history

- Original design: Python engine reads the PDF directly (PDF → AST → IR → CKO). Superseded.
- Current design: PDF processing is delegated entirely to Gemini Advanced. The Python
  engine's only input is `paper.json`.
