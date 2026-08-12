"""Structured logging setup.

Plain text in development, JSON in production. Every log line carries the
agent name and run ID so a 200-document run can be traced afterwards.

Threat model T-3: document text must never reach the logs. We log document
IDs and span coordinates instead. The redact processor enforces that.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from loupe.config.settings import settings

SENSITIVE_KEYS = {"text", "content", "document_text", "span_text", "api_key", "prompt"}


def _redact(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Strip document and credential content from every log record."""
    for key in list(event_dict):
        if key.lower() in SENSITIVE_KEYS:
            value = event_dict[key]
            length = len(value) if isinstance(value, str) else "?"
            event_dict[key] = f"<redacted:{length} chars>"
    return event_dict


def configure_logging() -> None:
    """Initialise structlog. Call once, at process start."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level.value,
    )

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _redact,
    ]
    processors.append(
        structlog.processors.JSONRenderer()
        if settings.log_json
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level.value)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """Return a bound logger for a module or agent."""
    return structlog.get_logger(name)