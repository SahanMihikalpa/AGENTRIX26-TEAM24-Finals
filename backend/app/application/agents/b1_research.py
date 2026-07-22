"""B1 · Research — gather raw evidence for a knowledge gap (local-first, web-fallback).

See [docs/agents/b1-research.md](../../../docs/agents/b1-research.md).
When A5 reports a ``GAP``, B1 goes and finds the missing information: it searches
the **local source pool first** (reliable, low-latency — the demo's primary path,
AD-7) and only falls back to the **live web** (restricted to the ``*.gov.lk``
allow-list, QA-7) when the pool is thin. The raw candidates are written to
``acquisition_buffer`` for B2 to curate.

Delta vs. docs (logged in docs/10): B1 is a pure orchestrator over the
``SourcePool`` + ``WebSearch`` ports. Fetch/parse (PyMuPDF/trafilatura) lives in
those adapters (Stage 3); the web fallback currently carries the result snippet as
evidence (richer full-page fetch is a noted enhancement). ``acquisition_loops`` is
incremented by the supervisor (Stage 5), not here.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.application.graph.state import GraphState
from app.domain.entities import SourceType
from app.domain.ports.source_pool import PooledDocument, SourcePool
from app.domain.ports.web_search import WebResult, WebSearch


class ResearchAgent:
    """Collect raw evidence (local pool → web fallback) into ``acquisition_buffer``."""

    def __init__(
        self,
        source_pool: SourcePool,
        web_search: WebSearch | None = None,
        *,
        allowlist: Sequence[str] = (),
        max_results: int = 5,
        min_local_results: int = 1,
    ) -> None:
        self._source_pool = source_pool
        self._web_search = web_search
        self._allowlist = list(allowlist)
        self._max_results = max_results
        self._min_local_results = min_local_results

    def __call__(self, state: GraphState) -> dict[str, Any]:
        query = self._query(state)

        pooled = self._source_pool.search(query, limit=self._max_results)
        buffer: list[dict[str, Any]] = [self._pool_entry(doc) for doc in pooled]

        # Local-first: only reach for the (slower, allow-listed) web if the pool
        # didn't give us enough.
        if len(pooled) < self._min_local_results and self._web_search is not None:
            results = self._web_search.search(
                query, allowlist=self._allowlist, max_results=self._max_results
            )
            buffer.extend(self._web_entry(result) for result in results)

        return {"acquisition_buffer": buffer}

    # ── helpers ──────────────────────────────────────────────────
    @staticmethod
    def _query(state: GraphState) -> str:
        intent = state["intent"]
        return str(
            intent.get("normalized_query")
            or intent.get("service_guess")
            or state["user_query"]
        )

    @staticmethod
    def _pool_entry(doc: PooledDocument) -> dict[str, Any]:
        return {
            "text": doc.text,
            "title": doc.title,
            "url": doc.url,
            "source_type": doc.source_type.value,
            "published_date": doc.published_date.isoformat() if doc.published_date else None,
            "origin": "pool",
        }

    @staticmethod
    def _web_entry(result: WebResult) -> dict[str, Any]:
        return {
            "text": result.snippet,
            "title": result.title,
            "url": result.url,
            "source_type": SourceType.PORTAL.value,
            "published_date": None,
            "origin": "web",
        }
