"""Tavily web-search adapter — the **primary** ``WebSearch`` (AD-7).

Uses the Tavily API (free tier). The official-domain allow-list (QA-7) is applied
twice for defense in depth: server-side via Tavily's ``include_domains`` and
locally via :func:`host_allowed` on every returned URL. The SDK is imported
lazily; a client may be injected for testing / DI.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.adapters.web_search.allowlist import host_allowed, normalized_domains
from app.domain.ports.web_search import WebResult


class TavilyWebSearch:
    """Tavily-backed web search restricted to the official-domain allow-list."""

    def __init__(self, api_key: str, *, client: Any = None) -> None:
        self._api_key = api_key
        self._client = client

    def _ensure_client(self) -> Any:
        if self._client is None:
            try:
                from tavily import TavilyClient
            except ImportError as exc:  # pragma: no cover - requires the tavily extra
                raise RuntimeError(
                    "tavily-python is not installed; install the backend "
                    "dependencies (`pip install -e .[dev]`)."
                ) from exc
            self._client = TavilyClient(api_key=self._api_key)
        return self._client

    def search(
        self, query: str, *, allowlist: Sequence[str], max_results: int = 5
    ) -> list[WebResult]:
        response = self._ensure_client().search(
            query=query,
            max_results=max_results,
            include_domains=normalized_domains(allowlist),
            search_depth="basic",
        )
        results: list[WebResult] = []
        for item in response.get("results", []):
            url = item.get("url", "")
            if not host_allowed(url, allowlist):
                continue
            results.append(
                WebResult(
                    title=item.get("title", ""),
                    url=url,
                    snippet=item.get("content", ""),
                )
            )
        return results
