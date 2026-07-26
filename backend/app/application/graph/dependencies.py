"""``GraphDependencies`` — the injectable bundle the graph is built from.

The graph builder (Stage 5) is **framework-pure and config-free**: it takes the
ports + tunables it needs through this container and never imports concrete
adapters or ``Settings``. The edge (``api/``, Stage 6) constructs this from the
real adapters and ``Settings`` values; tests construct it from fakes.

``store`` and ``retriever`` are separate ports (narrow dependencies per agent) but
are typically the **same** object — ``ChromaSqliteStore`` implements both.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.ports.cache import AnswerCache
from app.domain.ports.document_fetcher import DocumentFetcher
from app.domain.ports.embeddings import EmbeddingProvider
from app.domain.ports.knowledge import KnowledgeStore, Retriever
from app.domain.ports.llm import LLMProvider
from app.domain.ports.source_pool import SourcePool
from app.domain.ports.web_search import WebSearch


@dataclass(frozen=True, slots=True)
class GraphDependencies:
    """Ports + tunables wired into the agent nodes when the graph is built."""

    # ── ports ────────────────────────────────────────────────────
    llm: LLMProvider
    embedder: EmbeddingProvider
    store: KnowledgeStore
    retriever: Retriever
    source_pool: SourcePool
    web_search: WebSearch | None = None
    # Optional: fetch + parse a PDF a web result links to, so B1 ingests the full
    # document rather than its search snippet.
    document_fetcher: DocumentFetcher | None = None
    # Optional: when absent the graph simply never short-circuits (AD-12 is an
    # optimization, not correctness), which keeps existing tests wiring-free.
    answer_cache: AnswerCache | None = None

    # ── tunables (defaults mirror Settings; injected at the edge) ─
    confidence_threshold: float = 0.6  # AD-8 serving gate (τ)
    max_acquisition_loops: int = 2  # AD-2 gap-loop cap (N)
    top_k: int = 5
    max_questions: int = 4  # A3 interview cap
    grader_sufficient_above: float = 0.5  # A5 thresholds
    grader_gap_below: float = 0.3
    web_allowlist: Sequence[str] = ()  # QA-7 (e.g. ["gov.lk"])
    web_priority_domains: Sequence[str] = ()  # gazette/legal, searched first
    # B1's second tier: search beyond the allow-list when it yields nothing. What
    # it finds is capped below the serving threshold, so it is reviewed, not served.
    allow_unofficial_fallback: bool = False
    unofficial_max_confidence: float = 0.5
    # B2 source authority (confidence = authority * extraction certainty).
    web_official_authority: float = 0.75
    web_unofficial_authority: float = 0.5
