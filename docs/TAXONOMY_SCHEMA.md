# taxonomy.json — Format Specification (proposed, not yet frozen)

Status: design only. No curriculum content exists yet. This document specifies the
*shape* Gemini should convert the "QuestionVault Taxonomy Version 1.0" document into —
it invents no IDs, no chapters, no topics, no concepts. Every example below uses IDs
already observed in the one real `paper.json` seen so far (`ch_python_revision_tour`,
`top_control_structures`, `con_iteration_jump`, `qt_mcq`, ...) purely to illustrate the
container shape, not to propose new curriculum.

Not implemented. No loader, no domain model, no Sprint 6 code exists for this yet.

## Why this shape

Two independent structures, because they're genuinely different kinds of vocabulary:

1. **Curriculum hierarchy** — `units[].chapters[].topics[].concepts[]`, nested exactly
   the way a curriculum outline document already reads (Unit → Chapter → Topic →
   Concept). Nesting is the natural conversion target for an LLM reading a hierarchical
   document — mirroring visual/structural nesting is far more reliable for Gemini than
   asking it to invent and consistently reuse foreign-key references across what could
   be hundreds of nodes.
2. **`question_types`** — flat, one level, no hierarchy. It's a controlled vocabulary
   (`qt_mcq`, `qt_sql_query`, ...), not a curriculum tree, and paper.json never nests it
   under anything either.

**Every non-root node also carries an explicit parent-id field** (`unit_id` on a
Chapter, `chapter_id` on a Topic, `topic_id` on a Concept) *in addition to* its nesting
position. This is deliberate redundancy, not an oversight:

- **Relationship verification** (an explicit design goal): a loader can check that a
  node's declared parent-id matches where it's actually nested, catching a Gemini
  conversion mistake (e.g. a topic nested under the wrong chapter) as an internal
  self-contradiction in the file itself — before it ever gets used to validate a real
  paper.
- **Fast lookup**: building `chapter_of_topic`/`topic_of_concept` maps (exactly what
  `educational_analysis/reference.py` already needs) becomes a single flat pass reading
  each node's own parent-id field, rather than a depth-tracking tree walk. More direct,
  and independently checkable against the tree walk as a consistency check.
- **Future search / future CKO generation**: both want to look up "what chapter is this
  topic under" without re-walking a tree — an explicit field answers that in O(1)
  wherever the node ends up (a flattened index, a search document, a CKO's provenance),
  without needing the original nested structure at hand.

`sequence` (on every level) is transcription of the source document's existing order
(Unit 1, Unit 2, ... Chapter 1, Chapter 2, ...) — not new content — kept because
worksheet/mock-paper generation (future CKO generation) will need curriculum order, not
insertion or alphabetical order. Optional, since not every source document may make
order explicit.

`subject` at the top level exists so a loader can confirm a given `paper.json` is being
checked against the *right* taxonomy file — e.g. refuse to validate a Computer Science
paper against a Mathematics taxonomy — once more than one subject's taxonomy exists.

IDs are **not touched**: `chapter_id`/`topic_id`/`concept_id`/`question_type_id` must be
copied exactly from wherever they already exist (the source Taxonomy v1.0 document,
and/or already-observed usage in real `paper.json` files) — never re-slugged, never
re-cased, never re-prefixed.

## Top-level object

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | string | yes | Versions this *file format*, independent of paper.json's own `schema_version`. Same discipline as paper.json: frozen once real content lands, changed only on a deliberate, explicit decision. |
| `taxonomy_id` | string | yes | Unique identifier for this taxonomy document as a whole (not a node id) — lets multiple taxonomy files coexist later without collision. |
| `name` | string | yes | Human-readable label, e.g. `"QuestionVault Taxonomy — Computer Science"`. |
| `subject` | string | yes | Must exactly match the `paper_metadata.subject` value of any paper.json this taxonomy is meant to validate, e.g. `"COMPUTER SCIENCE"`. |
| `units` | array of Unit | yes | Non-empty in production. |
| `question_types` | array of QuestionType | yes | Non-empty in production. |

## Unit

| Field | Type | Required | Notes |
|---|---|---|---|
| `unit_id` | string | yes | Unique across the whole file. Preserve exactly as it exists in the source document. |
| `name` | string | yes | |
| `sequence` | integer ≥ 1 | no | Curriculum order. |
| `chapters` | array of Chapter | yes | Non-empty in production. |

## Chapter

| Field | Type | Required | Notes |
|---|---|---|---|
| `chapter_id` | string | yes | Must exactly match `classification.chapter` values already seen in paper.json (e.g. `ch_python_revision_tour`). |
| `unit_id` | string | yes | Must equal the `unit_id` of the Unit this chapter is nested under. |
| `name` | string | yes | |
| `sequence` | integer ≥ 1 | no | |
| `topics` | array of Topic | yes | Non-empty in production. |

## Topic

| Field | Type | Required | Notes |
|---|---|---|---|
| `topic_id` | string | yes | Must exactly match `classification.topic` values (e.g. `top_control_structures`). |
| `chapter_id` | string | yes | Must equal the `chapter_id` of the Chapter this topic is nested under. |
| `name` | string | yes | |
| `sequence` | integer ≥ 1 | no | |
| `concepts` | array of Concept | yes | Non-empty in production. |

## Concept (leaf — no children)

| Field | Type | Required | Notes |
|---|---|---|---|
| `concept_id` | string | yes | Must exactly match `classification.concept` values (e.g. `con_iteration_jump`). |
| `topic_id` | string | yes | Must equal the `topic_id` of the Topic this concept is nested under. |
| `name` | string | yes | |
| `sequence` | integer ≥ 1 | no | |

## QuestionType (flat — no hierarchy)

| Field | Type | Required | Notes |
|---|---|---|---|
| `question_type_id` | string | yes | Must exactly match `classification.question_type` values (e.g. `qt_mcq`). |
| `name` | string | yes | |
| `sequence` | integer ≥ 1 | no | |

## Illustrative example

Uses only IDs already observed in the real `paper.json` — nothing here is new
curriculum, it's a shape demonstration.

```json
{
  "schema_version": "1.0",
  "taxonomy_id": "questionvault_taxonomy_cs",
  "name": "QuestionVault Taxonomy — Computer Science",
  "subject": "COMPUTER SCIENCE",
  "units": [
    {
      "unit_id": "unit_programming",
      "name": "Programming",
      "sequence": 1,
      "chapters": [
        {
          "chapter_id": "ch_python_revision_tour",
          "unit_id": "unit_programming",
          "name": "Revision of Python",
          "sequence": 1,
          "topics": [
            {
              "topic_id": "top_control_structures",
              "chapter_id": "ch_python_revision_tour",
              "name": "Control Structures",
              "sequence": 1,
              "concepts": [
                {
                  "concept_id": "con_iteration_jump",
                  "topic_id": "top_control_structures",
                  "name": "Iteration and Jump Statements",
                  "sequence": 1
                }
              ]
            }
          ]
        }
      ]
    }
  ],
  "question_types": [
    { "question_type_id": "qt_mcq", "name": "Multiple Choice Question", "sequence": 1 }
  ]
}
```

## Fit with the existing engine (informational — no code changes yet)

Not required for this design, but for context on why the shape above was chosen: a
future loader could either (a) map this into Sprint 1's existing, unmodified
`Taxonomy`/`TaxonomyNode` domain model — trivial, since unit/chapter/topic/concept
nesting depth maps directly onto `TaxonomyNode.level` (0/1/2/3) — and then run the
existing `build_curriculum_index()` unchanged, or (b) build a `CurriculumIndex`
directly from the explicit parent-id fields, which is simpler and more defensive than
depth-tracking a generic tree. Either path requires zero changes to Sprint 1–5 code;
this is purely a note for whoever builds that loader later.

## What this document deliberately does not do

- No curriculum content — every `name` above is either copied from a real, observed ID
  or an obvious placeholder; none of it should be treated as real.
- No new IDs, no re-slugging, no re-casing of anything from the source document.
- No enrichment fields (`description`, `keywords`, aliases, ...) — they'd be easy to add
  later under a minor version bump if wanted, but adding them now without real content
  to put in them would be inventing structure the requirements didn't ask for.
- No loader, no domain model, no CLI wiring, no tests — Sprint 6 has not started.
