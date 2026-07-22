"""A4 · Retrieval (RAG) — fetch grounding evidence for the resolved case.

See [docs/agents/a4-retrieval.md](../../../docs/agents/a4-retrieval.md).
Embed the normalised query locally (AD-4) and vector-search ChromaDB for the
top-k chunks, filtered by ``service_id`` metadata. Scores are reported honestly
(no inflation) so A5 can detect genuine gaps.

Leanness (AD-3): A4 puts only chunk text + provenance into ``retrieved`` (what A5
needs to grade). The exact structured rows (``REQUIREMENT/FEE/OFFICE``) are read
straight from the store by A6 at generation time, so they never bloat the
checkpointed state — and A6 always sees rows added by a gap-loop acquisition.
"""

from __future__ import annotations

from typing import Any

from app.application.graph.serialization import retrieved_to_state
from app.application.graph.state import GraphState
from app.domain.ports.embeddings import EmbeddingProvider
from app.domain.ports.knowledge import Retriever


class RetrievalAgent:
    """Vector retrieval (+ metadata filter) producing scored, cited chunks."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        retriever: Retriever,
        *,
        top_k: int = 5,
    ) -> None:
        self._embedder = embedder
        self._retriever = retriever
        self._top_k = top_k

    def __call__(self, state: GraphState) -> dict[str, Any]:
        query_embedding = self._embedder.embed_query(self._query(state))
        filters: dict[str, object] | None = None
        if state["service_id"] is not None:
            filters = {"service_id": state["service_id"]}

        chunks = self._retriever.search(
            query_embedding, filters=filters, top_k=self._top_k
        )
        return {"retrieved": [retrieved_to_state(chunk) for chunk in chunks]}

    @staticmethod
    def _query(state: GraphState) -> str:
        intent = state["intent"]
        return str(intent.get("normalized_query") or state["user_query"])
