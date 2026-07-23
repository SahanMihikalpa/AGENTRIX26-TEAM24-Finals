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


# ── coverage signal (the thin-duplicate fix) ─────────────────────
class CapturingLLM(ScriptedLLM):
    """A ScriptedLLM that also keeps the exact prompts it was handed."""

    def __init__(self, decision: ServiceDisambiguation) -> None:
        super().__init__(structured={ServiceDisambiguation: decision})
        self.prompts: list[str] = []
        self.systems: list[str | None] = []

    def complete_structured(
        self, prompt: str, schema: type, *, system: str | None = None, temperature: float = 0.0
    ) -> object:
        self.prompts.append(prompt)
        self.systems.append(system)
        return super().complete_structured(prompt, schema, system=system, temperature=temperature)


def _disambiguate(kb: SeededKB, query: str = "land") -> CapturingLLM:
    llm = CapturingLLM(ServiceDisambiguation(service_id=kb.deed_service_id, confidence=0.9))
    ServiceIdentifierAgent(kb.store, llm)(_state(query))
    return llm


def test_candidates_are_annotated_with_what_the_kb_actually_holds(kb: SeededKB) -> None:
    """Without this the model only sees names, and a thin near-verbatim catalog
    entry beats the curated service it duplicates — leaving A6 nothing to render."""
    prompt = _disambiguate(kb).prompts[0]

    assert f"id={kb.deed_service_id}" in prompt
    assert "documented requirement(s)" in prompt
    assert "fee(s)" in prompt


def test_a_service_with_nothing_on_file_is_labelled_as_such(kb: SeededKB) -> None:
    # The seeded "Land Survey Request" has a variant but no requirements or fees.
    prompt = _disambiguate(kb).prompts[0]

    assert f"id={kb.survey_service_id}" in prompt
    assert "no documented requirements — cannot produce a checklist" in prompt


def test_the_system_prompt_explains_how_to_weigh_coverage(kb: SeededKB) -> None:
    system = _disambiguate(kb).systems[0]

    assert system is not None
    assert "documented requirements and fees" in system
    # It must not become an absolute rule: the gap loop depends on new, empty
    # services still being reachable when they are the only real match.
    assert "sole one that actually matches" in system
