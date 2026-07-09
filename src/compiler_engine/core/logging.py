"""Structured logging for the compilation engine.

Every pipeline stage gets its own logger via :func:`get_logger`, namespaced under
``compiler_engine.<stage>``, so stages can log independently while sharing one
configured output format.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

_ROOT_LOGGER_NAME = "compiler_engine"
_STANDARD_RECORD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)


class JsonFormatter(logging.Formatter):
    """Renders each log record as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_RECORD_ATTRS
        }
        if extras:
            payload["context"] = extras
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(*, level: str = "INFO", format: str = "json") -> None:
    """Configure the shared ``compiler_engine`` logger tree. Call once, at startup."""
    root_logger = logging.getLogger(_ROOT_LOGGER_NAME)
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    handler = logging.StreamHandler(stream=sys.stderr)
    if format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root_logger.addHandler(handler)
    root_logger.propagate = False


def get_logger(stage_name: str) -> logging.Logger:
    """Return the logger for a single pipeline stage, e.g. ``get_logger("paper_import")``."""
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{stage_name}")
