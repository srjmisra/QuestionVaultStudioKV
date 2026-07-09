from compiler_engine.pipeline.stage import StageResult, StageStatus


def test_ok_builds_a_success_result():
    result = StageResult.ok("paper_import", artifact_ids=("doc1",), warnings=("low confidence",))

    assert result.succeeded is True
    assert result.status is StageStatus.SUCCESS
    assert result.artifact_ids == ("doc1",)
    assert result.warnings == ("low confidence",)
    assert result.errors == ()


def test_fail_builds_a_failure_result():
    result = StageResult.fail("paper_import", errors=("file not found",))

    assert result.succeeded is False
    assert result.status is StageStatus.FAILED
    assert result.errors == ("file not found",)


def test_default_duration_is_zero_until_the_runner_sets_it():
    result = StageResult.ok("paper_import")
    assert result.duration_seconds == 0.0
