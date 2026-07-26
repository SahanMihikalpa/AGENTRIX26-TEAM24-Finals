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

import logging
from collections.abc import Sequence
from typing import Any

from app.application.graph.state import GraphState
from app.domain.entities import SourceType
from app.domain.ports.document_fetcher import DocumentFetcher
from app.domain.ports.source_pool import PooledDocument, SourcePool
from app.domain.ports.web_search import WebResult, WebSearch

_log = logging.getLogger(__name__)


class ResearchAgent:
    """Collect raw evidence (local pool → web fallback) into ``acquisition_buffer``."""

    def __init__(
        self,
        source_pool: SourcePool,
        web_search: WebSearch | None = None,
        *,
        allowlist: Sequence[str] = (),
        priority_domains: Sequence[str] = (),
        max_results: int = 5,
        min_local_results: int = 1,
        allow_unofficial_fallback: bool = False,
        document_fetcher: DocumentFetcher | None = None,
    ) -> None:
        self._source_pool = source_pool
        self._web_search = web_search
        self._allowlist = list(allowlist)
        # Authoritative legal/official domains (the gazette, acts) searched first
        # so they surface ahead of general results. A subset of the allow-list.
        self._priority_domains = list(priority_domains)
        self._max_results = max_results
        self._min_local_results = min_local_results
        # Optional: when set, a web result that links to a PDF is fetched in full
        # rather than represented by its search snippet.
        self._document_fetcher = document_fetcher
        self._allow_unofficial_fallback = allow_unofficial_fallback

    def __call__(self, state: GraphState) -> dict[str, Any]:
        query = self._query(state)

        pooled = self._source_pool.search(query, limit=self._max_results)
        buffer: list[dict[str, Any]] = [self._pool_entry(doc) for doc in pooled]

        # Local-first: only reach for the (slower, allow-listed) web if the pool
        # didn't give us enough.
        if len(pooled) < self._min_local_results and self._web_search is not None:
            official = self._official_search(query)
            buffer.extend(self._web_entry(result, official=True) for result in official)
            _log.info(
                "B1 research %r: %d pooled, %d official web result(s) from %s",
                query,
                len(pooled),
                len(official),
                sorted({_host(r.url) for r in official}) or "—",
            )

            # Some requests simply have no page on an official domain, and the
            # allow-listed search then returns nothing at all — a dead end for the
            # citizen. Searching wider gives the gap loop something to work with;
            # what it finds is marked unofficial so B3 caps its confidence below the
            # serving threshold and AD-8 routes it to a human for review instead of
            # into an answer.
            if not official and self._allow_unofficial_fallback:
                wider = self._web_search.search(
                    query,
                    allowlist=self._allowlist,
                    max_results=self._max_results,
                    unrestricted=True,
                )
                buffer.extend(self._web_entry(result, official=False) for result in wider)
                _log.info(
                    "B1 research %r: no official result, unrestricted tier found %d "
                    "(unofficial) from %s",
                    query,
                    len(wider),
                    sorted({_host(r.url) for r in wider}) or "—",
                )

        return {"acquisition_buffer": buffer}

    def _official_search(self, query: str) -> list[WebResult]:
        """Gather official results comprehensively: the **full allow-list budget**
        plus a few **gazette/legal** hits on top, de-duplicated by URL.

        The general allow-list gets its whole budget so a citizen always sees the
        how-to portals (``immigration.gov.lk`` and friends). The priority tier then
        contributes up to a few authoritative gazette/acts results that the general
        search missed, prepended so they read first. Additive, not a cap: gazette
        never crowds out the portals, and the portals never bury the gazette.
        """
        assert self._web_search is not None
        seen: set[str] = set()
        general: list[WebResult] = []
        for result in self._web_search.search(
            query, allowlist=self._allowlist, max_results=self._max_results
        ):
            if result.url and result.url not in seen:
                seen.add(result.url)
                general.append(result)

        priority: list[WebResult] = []
        if self._priority_domains:
            priority_cap = max(1, self._max_results // 2)
            for result in self._web_search.search(
                query, allowlist=self._priority_domains, max_results=self._max_results
            ):
                if len(priority) >= priority_cap:
                    break
                if result.url and result.url not in seen:
                    seen.add(result.url)
                    priority.append(result)

        return priority + general

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
            # The curated pool is official government material by construction.
            "official": True,
        }

    def _web_entry(self, result: WebResult, *, official: bool) -> dict[str, Any]:
        entry = {
            "text": result.snippet,
            "title": result.title,
            "url": result.url,
            "source_type": SourceType.PORTAL.value,
            "published_date": None,
            "origin": "web",
            "official": official,
        }
        # A search snippet is a poor proxy for a PDF's contents. When the result
        # links to one, fetch and parse it so B2 curates from the real document —
        # its title, date and medium ride along too. Any failure leaves the
        # snippet-backed entry untouched.
        if self._document_fetcher is not None and result.url:
            parsed = self._document_fetcher.fetch(result.url)
            if parsed is not None and parsed.text.strip():
                entry["text"] = parsed.text
                entry["source_type"] = parsed.source_type.value
                if parsed.title:
                    entry["title"] = parsed.title
                if parsed.published_date is not None:
                    entry["published_date"] = parsed.published_date.isoformat()
        return entry


def _host(url: str) -> str:
    """The host of a URL, for coverage logging (empty string if unparseable)."""
    from urllib.parse import urlparse

    return (urlparse(url).hostname or "").lower()
