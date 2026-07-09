"""Writes the export/ package to disk. Pure serialization: never modifies a CKO,
never re-sorts or re-shapes its fields — only the *order in which CKOs appear in the
array* is made deterministic (sorted by cko_id) by this module, since registry
iteration order isn't a guarantee this stage should depend on.

manifest.json/statistics.json need no explicit key-sort for determinism: they're
fixed-schema pydantic models, and CompilerBaseModel.to_json() already serializes
fields in a fixed declaration order every time. ckos.json is a plain JSON array of
each CKO's own to_dict() output, unmodified.
"""

from __future__ import annotations

import json
from pathlib import Path

from compiler_engine.domain.cko import CKO
from compiler_engine.publishing.models import ExportManifest, ExportStatistics

EXPORT_DIR_NAME = "export"


def write_export_package(
    output_folder: Path,
    manifest: ExportManifest,
    statistics: ExportStatistics,
    ckos: tuple[CKO, ...],
) -> Path:
    export_dir = output_folder / EXPORT_DIR_NAME
    export_dir.mkdir(parents=True, exist_ok=True)

    (export_dir / "manifest.json").write_text(manifest.to_json() + "\n", encoding="utf-8")
    (export_dir / "statistics.json").write_text(statistics.to_json() + "\n", encoding="utf-8")

    sorted_ckos = sorted(ckos, key=lambda cko: cko.cko_id)
    ckos_payload = json.dumps([cko.to_dict() for cko in sorted_ckos], indent=2)
    (export_dir / "ckos.json").write_text(ckos_payload + "\n", encoding="utf-8")

    return export_dir
