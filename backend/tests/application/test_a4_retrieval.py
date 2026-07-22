"""A4 · Retrieval (RAG) — vector search with metadata filtering."""

from __future__ import annotations

from app.application.agents.a4_retrieval import RetrievalAgent
from app.application.graph.state import GraphState, new_state
from tests.application.conftest import DeterministicEmbedder, SeededKB


def _state(service_id: int, normalized_query: str) -> GraphState:
    state = new_state("s", normalized_query)
    state["service_id"] = service_id
    state["intent"] = {"normalized_query": normalized_query}
    return state


def test_retrieves_chunks_with_provenance(kb: SeededKB, embedder: DeterministicEmbedder) -> None:
    agent = RetrievalAgent(embedder, kb.store, top_k=3)

    update = agent(_state(kb.deed_service_id, "land deed transfer inheritance death certificate"))

    retrieved = update["retrieved"]
    assert retrieved, "expected at least one chunk"
    top = retrieved[0]
    assert "land deed transfer" in top["content"]
    assert top["source_id"] is not None
    assert top["verification_status"] == "verified"
    assert top["service_id"] == kb.deed_service_id


def test_service_filter_excludes_other_services(
    kb: SeededKB, embedder: DeterministicEmbedder
) -> None:
    agent = RetrievalAgent(embedder, kb.store, top_k=5)

    update = agent(_state(kb.deed_service_id, "land"))

    # the survey chunk belongs to a different service and is filtered out
    assert all(chunk["service_id"] == kb.deed_service_id for chunk in update["retrieved"])
