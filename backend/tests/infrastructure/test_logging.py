"""Observability infra (Stage 7a) — correlation-id logging + tracing toggle."""

from __future__ import annotations

import logging
import os

import pytest

from app.infrastructure.logging import (
    _CorrelationIdFilter,
    configure_logging,
    configure_tracing,
    correlation_id_var,
    get_correlation_id,
)

_TRACING_VARS = (
    "LANGSMITH_TRACING",
    "LANGCHAIN_TRACING_V2",
    "LANGSMITH_API_KEY",
    "LANGCHAIN_API_KEY",
    "LANGSMITH_PROJECT",
)


def test_correlation_filter_stamps_the_active_id() -> None:
    cid_filter = _CorrelationIdFilter()
    record = logging.LogRecord("n", logging.INFO, "p", 1, "msg", None, None)
    token = correlation_id_var.set("abc123")
    try:
        assert cid_filter.filter(record) is True
        assert record.correlation_id == "abc123"
    finally:
        correlation_id_var.reset(token)


def test_default_correlation_id_outside_a_request() -> None:
    assert get_correlation_id() == "-"


def test_configure_logging_attaches_the_filter() -> None:
    configure_logging("INFO")
    handlers = logging.getLogger().handlers
    assert handlers
    assert any(
        any(isinstance(f, _CorrelationIdFilter) for f in h.filters) for h in handlers
    )


def test_tracing_is_off_unless_flag_and_key(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _TRACING_VARS:
        monkeypatch.delenv(var, raising=False)
    assert configure_tracing(enabled=False, api_key="k") is False
    assert configure_tracing(enabled=True, api_key=None) is False
    assert "LANGSMITH_TRACING" not in os.environ


def test_tracing_sets_env_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _TRACING_VARS:
        monkeypatch.delenv(var, raising=False)
    assert configure_tracing(enabled=True, api_key="secret", project="proj") is True
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGSMITH_API_KEY"] == "secret"
    assert os.environ["LANGSMITH_PROJECT"] == "proj"
