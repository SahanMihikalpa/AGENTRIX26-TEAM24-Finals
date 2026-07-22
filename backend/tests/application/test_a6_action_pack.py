"""A6 · Action-Pack Generator — grounded assembly + the confidence serving gate."""

from __future__ import annotations

from typing import Any

from app.application.agents.a6_action_pack import ActionPackAgent
from app.application.agents.schemas import ActionSteps
from app.application.graph.state import GraphState, new_state
from tests.application.conftest import ScriptedLLM, SeededKB


def _retrieved(*, status: str = "verified", confidence: float = 0.95) -> list[dict[str, Any]]:
    return [
        {
            "content": "land deed transfer inheritance",
            "score": 0.8,
            "service_id": 1,
            "chunk_index": 0,
            "source_id": 12,
            "source_title": "Land Registry Circular 2024",
            "source_url": "https://landregistry.gov.lk/circular",
            "verification_status": status,
            "confidence": confidence,
            "last_verified": "2026-06-20",
        }
    ]


def _state(
    kb: SeededKB,
    *,
    grade: str = "SUFFICIENT",
    district: str | None = "Galle",
    confidence: float = 0.95,
    retrieved: list[dict[str, Any]] | None = None,
) -> GraphState:
    state = new_state("s", "transfer my inherited land")
    state["service_id"] = kb.deed_service_id
    state["variant_id"] = kb.inheritance_variant_id
    state["slots"] = {"district": district} if district else {}
    state["grade"] = grade
    state["answer_confidence"] = confidence
    state["retrieved"] = retrieved if retrieved is not None else _retrieved()
    return state


def test_served_pack_is_grounded_in_store_rows(kb: SeededKB) -> None:
    update = ActionPackAgent(kb.store)(_state(kb))

    answer = update["answer"]
    assert answer is not None
    assert answer["fallback"] is False
    assert answer["service_label"] == "Land Deed Transfer (inheritance)"
    assert answer["district"] == "Galle"
    assert [doc["name"] for doc in answer["documents"]] == ["Death certificate"]
    assert answer["fees"][0] == {
        "label": "Stamp duty",
        "amount_lkr": "1000",
        "source_id": answer["fees"][0]["source_id"],
        "notes": "",
    }
    assert answer["estimated_cost_lkr"] == "1000"
    assert answer["office"]["name"] == "DS Galle"
    assert answer["verification"] == "verified"
    assert answer["citations"][0]["source_id"] == 12
    assert update["citations"] == answer["citations"]
    assert answer["steps"]  # default steps present


def test_sale_variant_selects_the_right_rows(kb: SeededKB) -> None:
    state = _state(kb)
    state["variant_id"] = kb.sale_variant_id

    answer = ActionPackAgent(kb.store)(state)["answer"]

    assert answer is not None
    assert [doc["name"] for doc in answer["documents"]] == ["Sale agreement"]
    assert answer["estimated_cost_lkr"] == "4000"
    assert answer["service_label"] == "Land Deed Transfer (sale)"


def test_gap_routes_to_fallback_pack(kb: SeededKB) -> None:
    answer = ActionPackAgent(kb.store)(_state(kb, grade="GAP"))["answer"]

    assert answer is not None
    assert answer["fallback"] is True
    assert answer["fallback_message"]
    assert answer["documents"] == []
    assert answer["office"]["name"] == "DS Galle"  # still tell them where to go


def test_confidence_gate_blocks_low_confidence_auto_gathered(kb: SeededKB) -> None:
    state = _state(kb, confidence=0.4, retrieved=_retrieved(status="auto_gathered", confidence=0.4))

    answer = ActionPackAgent(kb.store, confidence_threshold=0.6)(state)["answer"]

    assert answer is not None
    assert answer["fallback"] is True  # the gate fired (AD-8)
    assert answer["documents"] == []


def test_verified_facts_bypass_the_gate_even_when_confidence_low(kb: SeededKB) -> None:
    state = _state(kb, confidence=0.1, retrieved=_retrieved(status="verified", confidence=0.1))

    answer = ActionPackAgent(kb.store, confidence_threshold=0.6)(state)["answer"]

    assert answer is not None
    assert answer["fallback"] is False  # verified bypasses the confidence gate


def test_served_auto_gathered_above_threshold_is_labelled_pending(kb: SeededKB) -> None:
    state = _state(kb, confidence=0.9, retrieved=_retrieved(status="auto_gathered", confidence=0.9))

    answer = ActionPackAgent(kb.store, confidence_threshold=0.6)(state)["answer"]

    assert answer is not None
    assert answer["fallback"] is False
    assert answer["verification"] == "newly_gathered_pending_verification"


def test_llm_sequences_the_steps_when_available(kb: SeededKB) -> None:
    steps = ActionSteps(steps=["Gather the death certificate.", "Visit DS Galle.", "Pay LKR 1000."])
    agent = ActionPackAgent(kb.store, ScriptedLLM(structured={ActionSteps: steps}))

    answer = agent(_state(kb))["answer"]

    assert answer is not None
    assert answer["steps"] == ["Gather the death certificate.", "Visit DS Galle.", "Pay LKR 1000."]
