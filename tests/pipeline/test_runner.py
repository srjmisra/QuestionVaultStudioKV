from compiler_engine.core.config import CompilerConfig
from compiler_engine.core.errors import CompilerError
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.pipeline.runner import PipelineRunner
from compiler_engine.pipeline.stage import PipelineStage, StageResult


def _context(tmp_path) -> CompilerContext:
    config = CompilerConfig(
        import_workspace=tmp_path / "import",
        assets_folder=tmp_path / "assets",
        output_folder=tmp_path / "output",
    )
    return CompilerContext.create(config)


class RecordingStage(PipelineStage):
    """Appends its own name to context.state['order'] and always succeeds."""

    def __init__(self, name: str) -> None:
        self.stage_name = name

    def execute(self, context: CompilerContext) -> StageResult:
        context.state.setdefault("order", []).append(self.stage_name)
        return StageResult.ok(self.stage_name, artifact_ids=(f"{self.stage_name}-artifact",))


class RaisingStage(PipelineStage):
    stage_name = "raising_stage"

    def execute(self, context: CompilerContext) -> StageResult:
        raise CompilerError("deliberate failure")


class CrashingStage(PipelineStage):
    """Raises a plain, unexpected exception rather than a CompilerError."""

    stage_name = "crashing_stage"

    def execute(self, context: CompilerContext) -> StageResult:
        raise RuntimeError("bug inside the stage")


class RejectingInputsStage(PipelineStage):
    stage_name = "rejecting_inputs_stage"

    def validate_inputs(self, context: CompilerContext) -> None:
        raise CompilerError("required input missing")

    def execute(self, context: CompilerContext) -> StageResult:
        raise AssertionError("execute() must not run when validate_inputs() fails")


def test_stages_run_in_registration_order(tmp_path):
    runner = PipelineRunner()
    runner.register(RecordingStage("first")).register(RecordingStage("second"))

    context = _context(tmp_path)
    summary = runner.run(context)

    assert context.state["order"] == ["first", "second"]
    assert summary.succeeded is True
    assert [r.stage_name for r in summary.results] == ["first", "second"]


def test_registered_stages_are_exposed_in_order(tmp_path):
    runner = PipelineRunner()
    first, second = RecordingStage("first"), RecordingStage("second")
    runner.register(first).register(second)

    assert runner.stages == (first, second)


def test_halts_on_compiler_error_and_does_not_run_later_stages(tmp_path):
    runner = PipelineRunner()
    runner.register(RecordingStage("first")).register(RaisingStage()).register(
        RecordingStage("never_runs")
    )

    context = _context(tmp_path)
    summary = runner.run(context)

    assert summary.halted is True
    assert summary.succeeded is False
    assert context.state["order"] == ["first"]
    assert [r.stage_name for r in summary.results] == ["first", "raising_stage"]
    assert summary.results[-1].errors == ("deliberate failure",)


def test_unexpected_exception_is_captured_as_a_failed_result(tmp_path):
    runner = PipelineRunner()
    runner.register(CrashingStage())

    summary = runner.run(_context(tmp_path))

    assert summary.halted is True
    assert summary.results[0].succeeded is False
    assert "bug inside the stage" in summary.results[0].errors[0]


def test_validate_inputs_failure_prevents_execute(tmp_path):
    runner = PipelineRunner()
    runner.register(RejectingInputsStage())

    summary = runner.run(_context(tmp_path))

    assert summary.halted is True
    assert summary.results[0].errors == ("required input missing",)


def test_stage_failure_returned_directly_also_halts(tmp_path):
    class DirectlyFailingStage(PipelineStage):
        stage_name = "directly_failing_stage"

        def execute(self, context: CompilerContext) -> StageResult:
            return StageResult.fail(self.stage_name, errors=("bad input data",))

    runner = PipelineRunner()
    runner.register(RecordingStage("first")).register(DirectlyFailingStage()).register(
        RecordingStage("never_runs")
    )

    summary = runner.run(_context(tmp_path))

    assert summary.halted is True
    assert [r.stage_name for r in summary.results] == ["first", "directly_failing_stage"]


def test_execution_summary_reports_run_id_from_context(tmp_path):
    context = _context(tmp_path)
    runner = PipelineRunner()
    runner.register(RecordingStage("only"))

    summary = runner.run(context)

    assert summary.run_id == context.metadata.run_id


def test_each_stage_result_gets_a_non_negative_duration(tmp_path):
    runner = PipelineRunner()
    runner.register(RecordingStage("first"))

    summary = runner.run(_context(tmp_path))

    assert summary.results[0].duration_seconds >= 0.0
    assert summary.total_duration_seconds >= 0.0
