"""Structured logging for the SeshOps platform.

Configures structlog with environment-aware formatters (pretty console for
development, JSON-lines for staging/production) and per-request context
propagation via contextvars.  Every log event carries the ``service=seshops``
field so events are identifiable in aggregated logging backends.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import structlog

from app.core.config import Environment, settings

# Ensure log directory exists
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Per-request context ──────────────────────────────────────────────────────

_request_context: ContextVar[Dict[str, Any]] = ContextVar(
    "seshops_request_context", default={}
)


def bind_context(**kwargs: Any) -> None:
    """Attach key-value pairs to the current request's logging context."""
    current = _request_context.get()
    _request_context.set({**current, **kwargs})


def clear_context() -> None:
    """Reset the logging context at the end of a request lifecycle."""
    _request_context.set({})


def get_context() -> Dict[str, Any]:
    """Return the current request-scoped logging context."""
    return _request_context.get()


def _inject_context(
    _logger: Any, _method: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Structlog processor that merges request context into every event."""
    ctx = get_context()
    if ctx:
        event_dict.update(ctx)
    return event_dict


def _inject_service(
    _logger: Any, _method: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Stamp every log event with the SeshOps service identifier."""
    event_dict.setdefault("service", "seshops")
    event_dict.setdefault("environment", settings.ENVIRONMENT.value)
    return event_dict


# ── JSONL file handler ───────────────────────────────────────────────────────

def _log_file_path() -> Path:
    """Build a date-partitioned JSONL log path for the active environment."""
    prefix = settings.ENVIRONMENT.value
    return settings.LOG_DIR / f"{prefix}-{datetime.now().strftime('%Y-%m-%d')}.jsonl"


class JsonlFileHandler(logging.Handler):
    """Writes structured JSON-line entries to daily rotating files."""

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self.file_path = file_path

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "service": "seshops",
                "environment": settings.ENVIRONMENT.value,
            }
            if hasattr(record, "extra"):
                entry.update(record.extra)

            with open(self.file_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        except Exception:
            self.handleError(record)


# ── Structlog wiring ─────────────────────────────────────────────────────────

def _shared_processors(*, include_callsite: bool = True) -> List[Any]:
    """Return the structlog processor chain used by all output renderers."""
    procs: List[Any] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        _inject_context,
        _inject_service,
    ]

    if include_callsite:
        procs.append(
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.MODULE,
                }
            )
        )

    return procs


def _configure_logging() -> None:
    """Wire structlog and stdlib logging for the current environment."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    file_handler = JsonlFileHandler(_log_file_path())
    file_handler.setLevel(log_level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        handlers=[file_handler, console_handler],
    )

    callsite = settings.ENVIRONMENT in (Environment.DEVELOPMENT, Environment.TEST)
    procs = _shared_processors(include_callsite=callsite)

    renderer: Any
    if settings.LOG_FORMAT == "console":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*procs, renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ── Module initialisation ────────────────────────────────────────────────────

_configure_logging()

logger = structlog.get_logger()
logger.info(
    "seshops_logging_ready",
    environment=settings.ENVIRONMENT.value,
    log_level=settings.LOG_LEVEL,
    log_format=settings.LOG_FORMAT,
)
