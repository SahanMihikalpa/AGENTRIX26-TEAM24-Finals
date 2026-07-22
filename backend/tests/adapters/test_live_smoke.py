"""Key-gated live smoke tests for the external adapters (Stage 3).

These make **real, quota'd** network calls, so they are **opt-in**: a test runs
only when ``RUN_LIVE_TESTS=1`` is set *and* the relevant credential (read from the
environment / `.env`) is present. The default offline gate always skips them,
staying fast and hermetic; the team runs them on demand to confirm the real
wiring (model names, keys, endpoints):

    # backend/.env has GEMINI_API_KEY / GROQ_API_KEY / TAVILY_API_KEY
    RUN_LIVE_TESTS=1 pytest tests/adapters/test_live_smoke.py
"""

from __future__ import annotations

import os

import pytest

from app.adapters.llm.gemini import GeminiLLMProvider
from app.adapters.llm.groq import GroqLLMProvider
from app.adapters.web_search.allowlist import host_allowed
from app.adapters.web_search.ddg import DdgWebSearch
from app.adapters.web_search.tavily import TavilyWebSearch
from app.infrastructure.config import get_settings

_LIVE = bool(os.getenv("RUN_LIVE_TESTS"))
_settings = get_settings()
_ALLOWLIST = _settings.web_allowlist_domains

requires_gemini = pytest.mark.skipif(
    not (_LIVE and _settings.gemini_api_key), reason="set RUN_LIVE_TESTS=1 and GEMINI_API_KEY"
)
requires_groq = pytest.mark.skipif(
    not (_LIVE and _settings.groq_api_key), reason="set RUN_LIVE_TESTS=1 and GROQ_API_KEY"
)
requires_tavily = pytest.mark.skipif(
    not (_LIVE and _settings.tavily_api_key), reason="set RUN_LIVE_TESTS=1 and TAVILY_API_KEY"
)
requires_ddg = pytest.mark.skipif(not _LIVE, reason="set RUN_LIVE_TESTS=1 (keyless web call)")


@requires_gemini
def test_gemini_completes() -> None:
    provider = GeminiLLMProvider(_settings.gemini_api_key or "", model=_settings.llm_model)
    answer = provider.complete("Reply with exactly the word: OK")
    assert isinstance(answer, str)
    assert answer.strip()


@requires_groq
def test_groq_completes() -> None:
    provider = GroqLLMProvider(_settings.groq_api_key or "", model=_settings.llm_fallback_model)
    answer = provider.complete("Reply with exactly the word: OK")
    assert isinstance(answer, str)
    assert answer.strip()


@requires_tavily
def test_tavily_search_stays_on_allowlist() -> None:
    search = TavilyWebSearch(_settings.tavily_api_key or "")
    results = search.search("national identity card renewal", allowlist=_ALLOWLIST, max_results=5)
    assert all(host_allowed(r.url, _ALLOWLIST) for r in results)


@requires_ddg
def test_ddg_search_stays_on_allowlist() -> None:
    results = DdgWebSearch().search(
        "national identity card renewal", allowlist=_ALLOWLIST, max_results=5
    )
    assert all(host_allowed(r.url, _ALLOWLIST) for r in results)
