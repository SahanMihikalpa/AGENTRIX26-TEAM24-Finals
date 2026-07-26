"""GraphState factory + serialization helpers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.application.graph.serialization import action_pack_to_state, retrieved_to_state
from app.application.graph.state import continue_state, new_state
from app.domain.entities import (
    ActionPack,
    ActionPackOffice,
    ActionPackVerification,
    Citation,
    DocumentItem,
    FeeLine,
    RetrievedChunk,
    Source,
    SourceType,
    VerificationStatus,
)


def test_new_state_has_every_key_defaulted() -> None:
    state = new_state("sess-1", "transfer my land")
    assert state["session_id"] == "sess-1"
    assert state["user_query"] == "transfer my land"
    assert state["service_id"] is None
    assert state["service_unknown"] is False
    assert state["pending_question"] is None
    assert state["retrieved"] == []
    assert state["acquisition_loops"] == 0
    assert state["answer"] is None
    assert state["history"] == []
    assert state["carried_service_id"] is None
    # total TypedDict → every field present from the start
    assert len(state) == 22


# ── continue_state: the next turn of a live conversation ─────────
def _finished_turn() -> dict[str, object]:
    """A completed run, as the checkpointer would hand it back."""
    return {
        "user_query": "transfer my late father's land to my name",
        "history": [],
        "service_id": 1,
        "variant_id": 7,
        "slots": {"district": "Galle", "relationship": "father"},
        "answer": {"service_label": "Land Deed Transfer (sale-transfer)"},
        "retrieved": [{"content": "old chunk"}],
        "grade": "SUFFICIENT",
        "answer_confidence": 0.9,
        "acquisition_loops": 2,
        "asked_slots": ["condition", "district"],
        "pending_question": None,
    }


def test_continue_state_carries_the_conversational_context() -> None:
    state = continue_state(_finished_turn(), "sess-1", "what about Kandy?")

    assert state["user_query"] == "what about Kandy?"
    assert state["service_id"] == 1
    assert state["variant_id"] == 7
    assert state["slots"] == {"district": "Galle", "relationship": "father"}
    assert state["carried_service_id"] == 1, "so a topic switch can be detected"


def test_continue_state_clears_the_finished_runs_scratch() -> None:
    """Everything belonging to the previous answer must go, or A5/A6 would grade
    and render the old turn's evidence against the new question."""
    state = continue_state(_finished_turn(), "sess-1", "what about Kandy?")

    assert state["retrieved"] == []
    assert state["grade"] == ""
    assert state["answer"] is None
    assert state["answer_confidence"] == 0.0
    assert state["acquisition_loops"] == 0
    assert state["asked_slots"] == []
    assert state["pending_question"] is None


def test_continue_state_records_the_turn_in_history() -> None:
    state = continue_state(_finished_turn(), "sess-1", "what about Kandy?")

    assert state["history"] == [
        {"role": "user", "text": "transfer my late father's land to my name"},
        {"role": "assistant", "text": "Answered about: Land Deed Transfer (sale-transfer)"},
    ]


def test_history_is_a_rolling_window() -> None:
    """The state is checkpointed on every node, so history must not grow forever."""
    previous = _finished_turn()
    previous["history"] = [{"role": "user", "text": f"turn {i}"} for i in range(20)]

    state = continue_state(previous, "sess-1", "next")

    assert len(state["history"]) == 6
    assert state["history"][-1]["text"].startswith("Answered about:")


def test_continue_state_on_an_empty_previous_state_is_just_a_fresh_start() -> None:
    state = continue_state({}, "sess-1", "hello")

    assert state["history"] == []
    assert state["service_id"] is None
    assert state["carried_service_id"] is None


def test_retrieved_to_state_flattens_provenance() -> None:
    source = Source(
        id=12,
        title="Circular 2024",
        url="https://x.gov.lk",
        source_type=SourceType.CIRCULAR,
        retrieved_date=date(2026, 6, 20),
        confidence=0.9,
        verification_status=VerificationStatus.VERIFIED,
    )
    chunk = RetrievedChunk(
        content="stamp duty is 1000", score=0.83, source=source, service_id=3, chunk_index=0
    )

    flat = retrieved_to_state(chunk)

    assert flat["content"] == "stamp duty is 1000"
    assert flat["score"] == 0.83
    assert flat["source_id"] == 12
    assert flat["verification_status"] == "verified"
    assert flat["last_verified"] == "2026-06-20"


def test_action_pack_to_state_preserves_decimal_as_string() -> None:
    pack = ActionPack(
        service_label="Land Deed Transfer (inheritance)",
        district="Galle",
        documents=(DocumentItem(name="Death certificate", mandatory=True, source_id=12),),
        fees=(FeeLine(label="Stamp duty", amount_lkr=Decimal("1000.50"), source_id=12),),
        office=ActionPackOffice(
            name="DS Galle", address="Galle Fort", hours="9-4", district="Galle"
        ),
        steps=("Collect documents.", "Visit the office."),
        estimated_cost_lkr=Decimal("1000.50"),
        verification=ActionPackVerification.VERIFIED,
        citations=(
            Citation(
                title="Circular",
                url="https://x.gov.lk",
                last_verified=date(2026, 6, 20),
                source_id=12,
            ),
        ),
    )

    flat = action_pack_to_state(pack)

    assert flat["service_label"] == "Land Deed Transfer (inheritance)"
    assert flat["fees"][0]["amount_lkr"] == "1000.50"  # precise, not a float
    assert flat["estimated_cost_lkr"] == "1000.50"
    assert flat["verification"] == "verified"
    assert flat["office"]["name"] == "DS Galle"
    assert flat["citations"][0]["last_verified"] == "2026-06-20"
    assert flat["fallback"] is False
