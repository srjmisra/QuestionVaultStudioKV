from pathlib import Path

from compiler_engine.core.config import CompilerConfig
from compiler_engine.pipeline.context import CompilerContext
from compiler_engine.pipeline.registry import ArtifactRegistry
from compiler_engine.pipeline.workspace import WorkspaceManager


def _config(tmp_path):
    return CompilerConfig(
        import_workspace=tmp_path / "import",
        assets_folder=tmp_path / "assets",
        output_folder=tmp_path / "output",
    )


def test_create_builds_a_context_with_a_workspace_manager(tmp_path):
    context = CompilerContext.create(_config(tmp_path))

    assert isinstance(context.workspace, WorkspaceManager)
    assert isinstance(context.registry, ArtifactRegistry)
    assert context.current_document is None
    assert context.state == {}


def test_each_context_gets_its_own_run_id(tmp_path):
    config = _config(tmp_path)
    first = CompilerContext.create(config)
    second = CompilerContext.create(config)

    assert first.metadata.run_id != second.metadata.run_id


def test_for_document_returns_a_new_context_with_the_document_set(tmp_path):
    context = CompilerContext.create(_config(tmp_path))
    document = Path("paper.json")

    scoped = context.for_document(document)

    assert scoped.current_document == document
    assert context.current_document is None
    assert scoped.registry is context.registry
    assert scoped.metadata is context.metadata


def test_logger_for_namespaces_under_compiler_engine(tmp_path):
    context = CompilerContext.create(_config(tmp_path))
    logger = context.logger_for("paper_import")

    assert logger.name == "compiler_engine.paper_import"
