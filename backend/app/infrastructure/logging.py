"""Logging + tracing configuration (observability, QA-8).

Stdout logging with a **correlation id** woven into every line, so one request's
log lines (across the async handler and the threadpool that runs the sync graph)
can be grepped together. The id is carried in a :class:`contextvars.ContextVar`
(set per request by ``CorrelationIdMiddleware``) and injected into records by a
logging ``Filter`` — no parameter threading through the call stack.

Optional **LangSmith tracing** is enabled here too: when configured, the LangChain
env vars are set so LangGraph traces every agent run (QA-8); when not, nothing is
sent anywhere (free-tier safe).
"""

from __future__ import annotations

import logging
import os
import sys
from contextvars import ContextVar
from uuid import uuid4

# The current request's correlation id ("-" outside any request). Public so the
# ASGI middleware can ``.set()`` / ``.reset()`` it around each request.
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(correlation_id)s | %(name)s | %(message)s"


class _CorrelationIdFilter(logging.Filter):
    """Stamp every record with the active correlation id (so the format never fails)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once, with correlation ids, writing to stdout."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=_LOG_FORMAT,
        stream=sys.stdout,
        force=True,
    )
    correlation_filter = _CorrelationIdFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(correlation_filter)


def get_logger(name: str) -> logging.Logger:
    """Return a module logger. Use ``get_logger(__name__)`` at module scope."""
    return logging.getLogger(name)


# ── correlation id helpers ────────────────────────────────────────
def new_correlation_id() -> str:
    """A fresh, URL-safe correlation id."""
    return uuid4().hex


def get_correlation_id() -> str:
    """The correlation id for the current request (``"-"`` if none is set)."""
    return correlation_id_var.get()


# ── optional LangSmith tracing (QA-8) ─────────────────────────────
def configure_tracing(
    *, enabled: bool, api_key: str | None, project: str = "govguide"
) -> bool:
    """Enable LangSmith tracing via env vars when configured.

    Returns whether tracing was turned on. A no-op (returns ``False``) unless both
    the flag is set *and* an API key is present, so the default run stays offline.
    """
    if not (enabled and api_key):
        return False
    # Set both the current (LANGSMITH_*) and legacy (LANGCHAIN_*) names so the
    # installed LangChain version picks it up regardless.
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_API_KEY"] = api_key
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ.setdefault("LANGSMITH_PROJECT", project)
    return True
