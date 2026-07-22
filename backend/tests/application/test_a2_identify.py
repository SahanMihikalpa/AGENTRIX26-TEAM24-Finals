"""A2 · Service Identifier — catalog matching + optional LLM disambiguation."""

from __future__ import annotations

from app.application.agents.a2_identify import ServiceIdentifierAgent
from app.application.agents.schemas import ServiceDisambiguation
from app.application.graph.state import GraphState, new_state
from tests.application.conftest import ScriptedLLM, SeededKB


def _state(query: str, normalized: str | None = None) -> GraphState:
    state = new_state("s", query)
    state["intent"] = {"normalized_query": normalized or query}
    return state


def test_unique_candidate_is_resolved_without_llm(kb: SeededKB) -> None:
    agent = ServiceIdentifierAgent(kb.store)

    update = agent(_state("deed transfer"))

    assert update["service_id"] == kb.deed_service_id
    assert update["service_unknown"] is False


def test_no_candidate_is_unknown(kb: SeededKB) -> None:
    agent = ServiceIdentifierAgent(kb.store)

    update = agent(_state("renew my passport"))

    assert update["service_id"] is None
    assert update["service_unknown"] is True


def test_multiple_candidates_use_llm_disambiguation(kb: SeededKB) -> None:
    decision = ServiceDisambiguation(service_id=kb.deed_service_id, confidence=0.9)
    agent = ServiceIdentifierAgent(
        kb.store, ScriptedLLM(structured={ServiceDisambiguation: decision})
    )

    update = agent(_state("land"))  # matches both "Land Deed Transfer" and "Land Survey"

    assert update["service_id"] == kb.deed_service_id
    assert update["service_unknown"] is False


def test_low_confidence_disambiguation_is_unknown(kb: SeededKB) -> None:
    decision = ServiceDisambiguation(service_id=kb.deed_service_id, confidence=0.2)
    agent = ServiceIdentifierAgent(
        kb.store,
        ScriptedLLM(structured={ServiceDisambiguation: decision}),
        min_confidence=0.5,
    )

    update = agent(_state("land"))

    assert update["service_unknown"] is True


def test_multiple_candidates_without_llm_falls_back_to_top(kb: SeededKB) -> None:
    agent = ServiceIdentifierAgent(kb.store)  # no LLM

    update = agent(_state("land"))

    assert update["service_unknown"] is False
    assert update["service_id"] in {kb.deed_service_id, kb.survey_service_id}
