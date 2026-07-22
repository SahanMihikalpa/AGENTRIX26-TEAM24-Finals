"""DuckDuckGo web-search adapter — the **keyless fallback** ``WebSearch``.

Uses the ``ddgs`` package (no API key), so research still works when no Tavily
key is configured. DuckDuckGo has no server-side domain filter, so we (a) bias
the query with ``site:`` operators for the allow-listed domains and (b) over-fetch
and filter every URL locally with :func:`host_allowed` (QA-7). The SDK is imported
lazily; a client may be injected for testing / DI.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.adapters.web_search.allowlist import host_allowed, normalized_domains
from app.domain.ports.web_search import WebResult

# DuckDuckGo returns far more non-official hits than Tavily, so we request a wider
# pool and trim to ``max_results`` after the allow-list filter.
_OVERFETCH_FACTOR = 5


class DdgWebSearch:
    """DuckDuckGo-backed web search restricted to the official-domain allow-list."""

    def __init__(self, *, client: Any = None) -> None:
        self._client = client

    def _ensure_client(self) -> Any:
        if self._client is None:
            try:
                from ddgs import DDGS
            except ImportError as exc:  # pragma: no cover - requires the ddgs extra
                raise RuntimeError(
                    "ddgs is not installed; install the backend "
                    "dependencies (`pip install -e .[dev]`)."
                ) from exc
            self._client = DDGS()
        return self._client

    def search(
        self, query: str, *, allowlist: Sequence[str], max_results: int = 5
    ) -> list[WebResult]:
        raw = self._ensure_client().text(
            _scoped_query(query, allowlist), max_results=max_results * _OVERFETCH_FACTOR
        )
        results: list[WebResult] = []
        for item in raw:
            url = item.get("href") or item.get("url") or ""
            if not host_allowed(url, allowlist):
                continue
            results.append(
                WebResult(
                    title=item.get("title", ""),
                    url=url,
                    snippet=item.get("body") or item.get("snippet", ""),
                )
            )
            if len(results) >= max_results:
                break
        return results


def _scoped_query(query: str, allowlist: Sequence[str]) -> str:
    """Append ``site:`` operators so DuckDuckGo favours the allow-listed domains."""
    domains = normalized_domains(allowlist)
    if not domains:
        return query
    scope = " OR ".join(f"site:{domain}" for domain in domains)
    return f"{query} ({scope})"
