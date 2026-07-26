"""Multi-turn conversation on one session.

A completed thread used to be wiped on the next message, so a session was good for
exactly one run. These drive several turns down the same ``session_id`` and assert
the conversation actually continues.
"""

from __future__ import annotations

from typing import Any

from app.application.agents.schemas import (
    ActionSteps,
    IntentEntities,
    IntentExtraction,
)
from tests.api.conftest import ClientFactory, parse_sse

_SCRIPT: dict[type, Any] = {
    IntentExtraction: IntentExtraction(
        normalized_query="passport renewal",
        service_guess="passport_renewal",
        entities=IntentEntities(district="Colombo"),
    ),
    ActionSteps: ActionSteps(steps=["Bring your birth certificate"]),
}


def _turn(client: Any, message: str, session_id: str = "sess") -> list[tuple[str, dict[str, Any]]]:
    response = client.post("/api/chat", json={"message": message, "session_id": session_id})
    assert response.status_code == 200
    return parse_sse(response.text)


def _pack(events: list[tuple[str, dict[str, Any]]]) -> dict[str, Any] | None:
    packs = [data for event, data in events if event == "action_pack"]
    return packs[0] if packs else None


def test_a_second_turn_still_answers(build_client: ClientFactory) -> None:
    client, _ = build_client(_SCRIPT)

    first = _turn(client, "renew my passport")
    second = _turn(client, "what about Kandy?")

    assert _pack(first) is not None
    assert _pack(second) is not None, "the session must not be spent after one run"


def test_the_session_survives_many_turns(build_client: ClientFactory) -> None:
    client, _ = build_client(_SCRIPT)

    for turn in range(5):
        events = _turn(client, f"question {turn}")
        assert [e for e, _ in events][-1] == "done"
        assert _pack(events) is not None


def test_context_carries_into_the_next_turn(build_client: ClientFactory) -> None:
    """The follow-up keeps the service it inherited rather than starting over."""
    client, _ = build_client(_SCRIPT)
    _turn(client, "renew my passport")

    pack = _pack(_turn(client, "what about Kandy?"))

    assert pack is not None
    assert pack["service_label"].startswith("Passport Renewal")


def test_each_turn_gets_a_fresh_answer_not_the_previous_one(
    build_client: ClientFactory,
) -> None:
    """Scratch from the finished run must be cleared, or A5/A6 would grade the old
    turn's evidence against the new question."""
    client, _ = build_client(_SCRIPT)
    _turn(client, "renew my passport")

    events = _turn(client, "renew my passport")
    steps = [data["id"] for event, data in events if event == "step"]

    assert "understand" in steps, "the new turn runs the pipeline again"
    assert _pack(events) is not None


def test_action_pack_fetch_returns_the_latest_turn(build_client: ClientFactory) -> None:
    client, _ = build_client(_SCRIPT)
    _turn(client, "renew my passport")
    _turn(client, "what about Kandy?")

    response = client.get("/api/sessions/sess/action-pack")

    assert response.status_code == 200
    assert response.json()["service_label"].startswith("Passport Renewal")
