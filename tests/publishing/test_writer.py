import json
from datetime import datetime, timezone

from compiler_engine.domain.cko import CKO, CkoEvolution, CkoLineage, CkoOccurrence, CkoRelationships, CkoStatus
from compiler_engine.domain.educational_analysis import EducationalAnalysis
from compiler_engine.paper_import.schema import RawContent, TextBlock
from compiler_engine.publishing.models import ExportManifest, ExportStatistics
from compiler_engine.publishing.writer import write_export_package


def _cko(cko_id: str, stem: str) -> CKO:
    occurrence = CkoOccurrence(
        paper_id="p1", examination="Exam", session="2025-26", region="Delhi",
        original_question_number="1", allocated_marks=1,
    )
    return CKO(
        cko_id=cko_id, version=1, checksum=cko_id, created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc), status=CkoStatus.UNDER_REVIEW,
        classification=EducationalAnalysis(question_id="Q1", subject="CS", topic="top_x"),
        content=RawContent(blocks=(TextBlock(block_type="text", value=stem),)), options=None,
        relationships=CkoRelationships(), lineage=CkoLineage(occurrences=(occurrence,)),
        evolution=CkoEvolution(),
    )


def _manifest() -> ExportManifest:
    return ExportManifest(
        generated_at=datetime.now(timezone.utc), compiler_version="0.1.0",
        taxonomy_version="1.0", paper_count=1, question_count=2, cko_count=2,
    )


def _statistics() -> ExportStatistics:
    return ExportStatistics(
        papers_processed=1, questions_imported=2, ckos_created=2,
        duplicate_questions_merged=0, orphan_relationships_skipped=0,
        validation_warnings=0, validation_errors=0,
    )


def test_writes_all_three_files_under_export_subfolder(tmp_path):
    export_dir = write_export_package(tmp_path, _manifest(), _statistics(), (_cko("cko_b", "B"), _cko("cko_a", "A")))

    assert export_dir == tmp_path / "export"
    assert (export_dir / "manifest.json").is_file()
    assert (export_dir / "statistics.json").is_file()
    assert (export_dir / "ckos.json").is_file()


def test_manifest_and_statistics_content_round_trips(tmp_path):
    manifest, statistics = _manifest(), _statistics()
    export_dir = write_export_package(tmp_path, manifest, statistics, ())

    assert ExportManifest.from_json((export_dir / "manifest.json").read_text()) == manifest
    assert ExportStatistics.from_json((export_dir / "statistics.json").read_text()) == statistics


def test_ckos_are_written_sorted_by_cko_id_regardless_of_input_order(tmp_path):
    export_dir = write_export_package(
        tmp_path, _manifest(), _statistics(), (_cko("cko_b", "B"), _cko("cko_a", "A"))
    )

    payload = json.loads((export_dir / "ckos.json").read_text())
    assert [entry["cko_id"] for entry in payload] == ["cko_a", "cko_b"]


def test_ckos_json_contains_every_field_unmodified(tmp_path):
    cko = _cko("cko_a", "Exact wording")
    export_dir = write_export_package(tmp_path, _manifest(), _statistics(), (cko,))

    payload = json.loads((export_dir / "ckos.json").read_text())
    assert payload[0] == cko.to_dict()


def test_creates_export_directory_if_missing(tmp_path):
    output_folder = tmp_path / "does_not_exist_yet"
    export_dir = write_export_package(output_folder, _manifest(), _statistics(), ())
    assert export_dir.is_dir()
