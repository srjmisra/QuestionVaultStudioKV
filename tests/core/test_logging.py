import json
import logging

from compiler_engine.core.logging import JsonFormatter, configure_logging, get_logger


def test_get_logger_namespaces_under_compiler_engine():
    logger = get_logger("paper_import")
    assert logger.name == "compiler_engine.paper_import"


def test_different_stages_get_independent_loggers():
    assert get_logger("paper_import") is not get_logger("relationship_resolution")


def test_json_formatter_produces_valid_json_with_expected_fields():
    logger = logging.getLogger("compiler_engine.test_json_formatter")
    record = logger.makeRecord(
        name=logger.name,
        level=logging.INFO,
        fn="test",
        lno=1,
        msg="parsed page",
        args=(),
        exc_info=None,
        extra={"page_number": 3},
    )
    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "compiler_engine.test_json_formatter"
    assert payload["message"] == "parsed page"
    assert payload["context"] == {"page_number": 3}
    assert "timestamp" in payload


def test_configure_logging_attaches_a_single_handler_to_the_root_logger():
    configure_logging(level="DEBUG", format="json")
    configure_logging(level="DEBUG", format="json")

    root_logger = logging.getLogger("compiler_engine")
    assert len(root_logger.handlers) == 1
    assert root_logger.level == logging.DEBUG
