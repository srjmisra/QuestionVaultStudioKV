"""Deterministic, content-only checksum used to deduplicate questions into CKOs.

Depends ONLY on a question's content blocks and options — explicitly not on paper_id,
question_id, timestamps, or JSON key ordering. `classification` is deliberately
excluded too: it's Gemini's judgment call, which can legitimately differ slightly
between two extractions of the literally identical question (a borderline concept
tagged one way in one paper, another way in a second), whereas the question's own
wording and options are its actual, objective identity. Block *order* within a question
is preserved and does affect the checksum — that's meaningful content, not a JSON
formatting artifact, unlike dict key order, which `sort_keys=True` neutralizes.

No text normalization happens here. Two occurrences differing by even one character
(including whitespace) will not match — a deliberate consequence of "never normalize
educational text," not an oversight.
"""

from __future__ import annotations

import hashlib
import json

from compiler_engine.paper_import.schema import RawContent, RawOption


def compute_checksum(content: RawContent, options: tuple[RawOption, ...] | None) -> str:
    payload = {
        "content": content.model_dump(mode="json"),
        "options": [option.model_dump(mode="json") for option in options] if options else None,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
