from datetime import datetime, timezone

from compiler_engine.publishing.models import (
    CHECKSUM_ALGORITHM,
    EXPORT_FORMAT_VERSION,
    ExportManifest,
    ExportStatistics,
)


def test_manifest_defaults_match_current_export_format():
    manifest = ExportManifest(
        generated_at=datetime.now(timezone.utc),
        compiler_version="0.1.0",
        paper_count=1,
        question_count=1,
        cko_count=1,
    )
    assert manifest.export_version == EXPORT_FORMAT_VERSION
    assert manifest.checksum_algorithm == CHECKSUM_ALGORITHM
    assert manifest.taxonomy_version is None


def test_manifest_round_trips_through_json():
    manifest = ExportManifest(
        generated_at=datetime.now(timezone.utc),
        compiler_version="0.1.0",
        taxonomy_version="1.0",
        paper_count=2,
        question_count=10,
        cko_count=9,
    )
    assert ExportManifest.from_json(manifest.to_json()) == manifest


def test_statistics_round_trips_through_json():
    statistics = ExportStatistics(
        papers_processed=1,
        questions_imported=49,
        ckos_created=49,
        duplicate_questions_merged=0,
        orphan_relationships_skipped=1,
        validation_warnings=8,
        validation_errors=3,
    )
    assert ExportStatistics.from_json(statistics.to_json()) == statistics
