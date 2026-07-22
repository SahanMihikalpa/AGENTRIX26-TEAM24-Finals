"""``WebSearch`` port — the live-web fallback socket (B1).

Implemented by ``adapters/web_search/tavily.py`` (primary) and ``ddg.py``
(keyless fallback). Calls are restricted to an allow-list of official domains
(QA-7); enforcement lives in the adapter.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class WebResult:
    """A single web search hit."""

    title: str
    url: str
    snippet: str


@runtime_checkable
class WebSearch(Protocol):
    """A swappable web-search backend."""

    def search(
        self, query: str, *, allowlist: Sequence[str], max_results: int = 5
    ) -> list[WebResult]:
        """Search the web, returning only results whose host is in ``allowlist``."""
        ...
