"""Logging configuration.

A minimal, dependency-free logging setup for now. Per-session correlation ids
and optional LangSmith tracing are added in Stage 7 (hardening); keeping this
small avoids premature structure.
"""

from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once, writing structured-ish lines to stdout."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=_LOG_FORMAT,
        stream=sys.stdout,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a module logger. Use `get_logger(__name__)` at module scope."""
    return logging.getLogger(name)
