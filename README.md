# QuestionVault Studio

Python Knowledge Import & Publishing Engine for the KV Coders question import pipeline.

Consumes a Gemini Advanced-generated `paper.json` — never the original PDF — and turns
it into validated, publishable Canonical Knowledge Objects for later review and
publishing through the existing KV Coders PHP admin interface.
See `docs/ARCHITECTURE.md` for the full, finalized architecture.

## Scope of this repository

QuestionVault Studio is a new module inside the existing KV Coders educational
platform (PHP 8 + MySQL, Bluehost). It has two independent parts; this
repository contains **only** Part A, the Python engine. Part B, the KV Coders
Admin Module, lives in the existing KV Coders website repo and is out of scope
here. Part A never connects to MySQL or to the live website — it stops at
producing publishable JSON artifacts.

## Layout

- `src/compiler_engine/` — pipeline stages: `paper_import`, `educational_analysis`,
  `relationship_resolution`, `canonical_knowledge_object_generation`,
  `database_export`, `validation`
- `tests/` — mirrors the pipeline stage layout
- `docs/` — architecture reference
