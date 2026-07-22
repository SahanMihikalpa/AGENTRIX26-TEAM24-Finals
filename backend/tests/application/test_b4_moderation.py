"""B4 · Moderation Gate — serve-but-label queueing (no blocking)."""

from __future__ import annotations

from typing import Any

from app.application.agents.b4_moderation import ModerationGateAgent
from app.application.graph.state import GraphState, new_state


def _record(
    *,
    status: str = "auto_gathered",
    confidence: float = 0.4,
    origin: str = "web",
    url: str = "https://doc.gov.lk/biz",
    service: str = "Business Name Registration",
) -> dict[str, Any]:
    return {
        "source": {
            "title": "Business Reg Circular",
            "url": url,
            "verification_status": status,
            "confidence": confidence,
            "origin": origin,
        },
        "extraction": {"service_name": service},
    }


def _state(*records: dict[str, Any], queue: list[dict[str, Any]] | None = None) -> GraphState:
    state = new_state("s", "register a business name")
    state["curated"] = list(records)
    state["moderation_queue"] = queue or []
    return state


def test_queues_auto_gathered_items_for_review() -> None:
    update = ModerationGateAgent(confidence_threshold=0.6)(_state(_record(confidence=0.4)))

    queue = update["moderation_queue"]
    assert len(queue) == 1
    assert queue[0]["status"] == "pending"
    assert queue[0]["needs_review"] is True  # low confidence and web origin
    assert queue[0]["service_name"] == "Business Name Registration"


def test_verified_items_are_not_queued() -> None:
    update = ModerationGateAgent()(_state(_record(status="verified")))

    assert update["moderation_queue"] == []


def test_high_confidence_pool_item_is_queued_but_not_flagged() -> None:
    record = _record(status="auto_gathered", confidence=0.9, origin="pool")

    queue = ModerationGateAgent(confidence_threshold=0.6)(_state(record))["moderation_queue"]

    assert len(queue) == 1
    assert queue[0]["needs_review"] is False  # confident + local origin


def test_dedups_against_existing_queue() -> None:
    existing = [{"url": "https://doc.gov.lk/biz", "source_title": "Business Reg Circular"}]

    queue = ModerationGateAgent()(_state(_record(), queue=existing))["moderation_queue"]

    assert len(queue) == 1  # the same source isn't queued twice across loops
