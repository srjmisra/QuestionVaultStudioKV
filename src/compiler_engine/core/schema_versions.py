"""Single source of truth for the schema version of each domain artifact.

Bump the relevant entry whenever a domain model's on-disk JSON shape changes in a
way that older consumers (the KV Coders Admin Module) need to know about.
"""

from __future__ import annotations

CURRENT_SCHEMA_VERSIONS: dict[str, str] = {
    "document_ast": "1.0.0",
    "question_ir": "1.0.0",
    "answer_ir": "1.0.0",
    "educational_analysis": "1.0.0",
    "canonical_knowledge_object": "1.0.0",
    "validation_report": "1.0.0",
    "taxonomy": "1.0.0",
    "relationship_graph": "1.0.0",
}
