"""Composition root — assemble the concrete adapters into a runnable graph.

This is the one place that knows about **both** ``Settings`` and the concrete
adapters; the application/graph layers stay config- and adapter-free (they receive
``GraphDependencies``). Everything the adapters need is lazy (SDKs, the bge model),
so ``build_runtime`` is cheap and key-free to call — the model load and first LLM
call happen on the first real request.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from fastapi import Request
from langgraph.checkpoint.sqlite import SqliteSaver

from app.adapters.embeddings.bge import BgeEmbeddingProvider
from app.adapters.knowledge.chroma_sqlite import ChromaSqliteStore
from app.adapters.llm.gemini import GeminiLLMProvider
from app.adapters.llm.groq import GroqLLMProvider
from app.adapters.parser.pymupdf import PyMuPdfSourceParser
from app.adapters.source_pool.filesystem import FilesystemSourcePool
from app.adapters.web_search.ddg import DdgWebSearch
from app.adapters.web_search.tavily import TavilyWebSearch
from app.application.feedback import ExperienceReportIntake
from app.application.graph import GraphDependencies
from app.application.graph.builder import build_graph
from app.application.moderation import ModerationService
from app.domain.ports.cache import AnswerCache
from app.domain.ports.embeddings import EmbeddingProvider
from app.domain.ports.llm import LLMProvider
from app.domain.ports.web_search import WebSearch
from app.infrastructure.cache import InMemoryAnswerCache
from app.infrastructure.config import Settings
from app.infrastructure.llm_gateway import LLMGateway
from app.infrastructure.logging import get_logger

_log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class AppRuntime:
    """The wired backend: the compiled graph plus the use cases the API needs."""

    graph: Any  # CompiledStateGraph
    store: ChromaSqliteStore
    cache: AnswerCache
    settings: Settings
    experience_intake: ExperienceReportIntake  # POST /api/experience-reports
    moderation: ModerationService  # /api/moderation/*


def build_runtime(settings: Settings) -> AppRuntime:
    """Construct every adapter, wire the graph, and mount the SQLite checkpointer."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    store = ChromaSqliteStore(
        sqlite_path=settings.sqlite_path, chroma_dir=settings.chroma_dir
    )
    llm: LLMProvider = _build_llm(settings)
    embedder: EmbeddingProvider = BgeEmbeddingProvider(settings.embedding_model)
    cache = InMemoryAnswerCache()
    deps = GraphDependencies(
        llm=llm,
        embedder=embedder,
        store=store,
        retriever=store,
        source_pool=FilesystemSourcePool(
            settings.source_pool_dir, parser=PyMuPdfSourceParser()
        ),
        web_search=_build_web_search(settings),
        confidence_threshold=settings.confidence_threshold,
        max_acquisition_loops=settings.max_acquisition_loops,
        web_allowlist=settings.web_allowlist_domains,
        cache=cache,  # AD-12 short-circuit + per-service invalidation on B3 upsert
    )
    graph = build_graph(deps, checkpointer=_build_checkpointer(settings))
    _log.info("Runtime built (graph compiled, checkpointer mounted)")
    return AppRuntime(
        graph=graph,
        store=store,
        cache=cache,
        settings=settings,
        # The feedback path reuses the same B2/B3 agents (over the same store +
        # embedder), so citizen reports grow the KB exactly like the gap loop.
        experience_intake=ExperienceReportIntake(store, llm, embedder),
        # Moderation shares the cache so promote/reject invalidate stale answers.
        moderation=ModerationService(store, cache),
    )


def get_runtime(request: Request) -> AppRuntime:
    """FastAPI dependency: the app's runtime, built lazily and cached on first use.

    Building is lazy (the bge model loads on first embed), so the first ``/api/chat``
    request pays the warm-up; subsequent requests reuse the same graph. Tests
    override this dependency, so they never construct real stores or hit the network.
    """
    runtime: AppRuntime | None = getattr(request.app.state, "runtime", None)
    if runtime is None:
        runtime = build_runtime(request.app.state.settings)
        request.app.state.runtime = runtime
    return runtime


# ── internals ────────────────────────────────────────────────────
def _build_llm(settings: Settings) -> LLMProvider:
    """Gemini primary, optional Groq fallback, behind the rate-limited gateway."""
    primary = GeminiLLMProvider(settings.gemini_api_key or "", model=settings.llm_model)
    fallback: LLMProvider | None = (
        GroqLLMProvider(settings.groq_api_key, model=settings.llm_fallback_model)
        if settings.groq_api_key
        else None
    )
    return LLMGateway(
        primary, fallback=fallback, rate_limit_rpm=settings.llm_rate_limit_rpm
    )


def _build_web_search(settings: Settings) -> WebSearch:
    """Tavily when a key is set; otherwise the keyless DuckDuckGo fallback."""
    if settings.tavily_api_key:
        return TavilyWebSearch(settings.tavily_api_key)
    return DdgWebSearch()


def _build_checkpointer(settings: Settings) -> SqliteSaver:
    """A persistent ``SqliteSaver`` so the A3 interview resumes across requests (AD-3)."""
    conn = sqlite3.connect(
        str(settings.data_dir / "checkpoints.sqlite3"), check_same_thread=False
    )
    return SqliteSaver(conn)
