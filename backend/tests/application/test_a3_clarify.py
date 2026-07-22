"""A3 · Clarification — minimal, resumable slot-filling interview."""

from __future__ import annotations

from typing import Any

from app.application.agents.a3_clarify import ClarificationAgent
from app.application.agents.schemas import ClarificationQuestion
from app.application.graph.state import GraphState, new_state
from tests.application.conftest import ScriptedLLM, SeededKB


def _state(
    service_id: int,
    *,
    slots: dict[str, Any] | None = None,
    asked: list[str] | None = None,
    variant_id: int | None = None,
) -> GraphState:
    state = new_state("s", "q")
    state["service_id"] = service_id
    state["slots"] = slots or {}
    state["asked_slots"] = asked or []
    state["variant_id"] = variant_id
    return state


def test_asks_for_the_variant_when_several_exist(kb: SeededKB) -> None:
    agent = ClarificationAgent(kb.store)

    update = agent(_state(kb.deed_service_id))

    question = update["pending_question"]
    assert question is not None
    assert question["slot"] == "condition"
    assert set(question["options"]) == {"inheritance", "sale"}
    assert update["asked_slots"] == ["condition"]
    assert "variant_id" not in update  # not resolved yet


def test_resolves_variant_from_filled_condition_slot(kb: SeededKB) -> None:
    agent = ClarificationAgent(kb.store)

    slots = {"condition": "inheritance", "district": "Galle"}
    update = agent(_state(kb.deed_service_id, slots=slots))

    assert update["pending_question"] is None
    assert update["variant_id"] == kb.inheritance_variant_id


def test_resolves_variant_from_the_user_query_text(kb: SeededKB) -> None:
    # The citizen already named the variant ("by sale") in their request, so A3 should
    # pin it from their own words instead of asking a redundant clarification.
    agent = ClarificationAgent(kb.store)
    state = _state(kb.deed_service_id, slots={"district": "Galle"})
    state["user_query"] = "I want to transfer my land by sale"

    update = agent(state)

    assert update["pending_question"] is None
    assert update["variant_id"] == kb.sale_variant_id


def test_resolves_variant_from_a1_relationship_entity(kb: SeededKB) -> None:
    agent = ClarificationAgent(kb.store)

    # A1 seeds the variant condition as `relationship`; A3 should bridge it to the
    # `condition` slot and not ask a redundant question.
    slots = {"relationship": "sale", "district": "Galle"}
    update = agent(_state(kb.deed_service_id, slots=slots))

    assert update["pending_question"] is None
    assert update["variant_id"] == kb.sale_variant_id


def test_single_variant_service_auto_resolves(kb: SeededKB) -> None:
    agent = ClarificationAgent(kb.store)

    update = agent(_state(kb.survey_service_id, slots={"district": "Galle"}))

    assert update["pending_question"] is None
    assert update["variant_id"] == kb.survey_variant_id


def test_asks_for_district_when_missing(kb: SeededKB) -> None:
    agent = ClarificationAgent(kb.store)

    update = agent(_state(kb.survey_service_id))  # variant resolvable, district missing

    question = update["pending_question"]
    assert question is not None
    assert question["slot"] == "district"
    assert question["allow_free_text"] is True


def test_question_cap_defaults_to_most_common_variant(kb: SeededKB) -> None:
    agent = ClarificationAgent(kb.store)

    # both slots already asked but condition never resolved → default, don't loop
    update = agent(_state(kb.deed_service_id, asked=["condition", "district"]))

    assert update["pending_question"] is None
    assert update["variant_id"] == kb.inheritance_variant_id  # first/most-common variant


def test_llm_rephrases_but_options_stay_grounded(kb: SeededKB) -> None:
    phrased = ClarificationQuestion(question="Is this an inheritance, sale, or gift?", options=[])
    agent = ClarificationAgent(kb.store, ScriptedLLM(structured={ClarificationQuestion: phrased}))

    update = agent(_state(kb.deed_service_id))

    question = update["pending_question"]
    assert question is not None
    assert question["question"] == "Is this an inheritance, sale, or gift?"
    assert set(question["options"]) == {"inheritance", "sale"}  # from the catalog, not the LLM
