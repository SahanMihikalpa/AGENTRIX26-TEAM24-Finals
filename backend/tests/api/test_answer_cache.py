"""AD-12 — the AnswerCache short-circuit, observed through the SSE stream.

A cache hit is detectable without reaching into internals: the run skips A4→A5→A6,
so no ``lookup`` progress pill is ever emitted, while the ``action_pack`` the
client receives is byte-identical to the generated one.
"""

from __future__ import annotations

from typing import Any

from app.application.agents.schemas import ActionSteps, IntentEntities, IntentExtraction
from tests.api.conftest import ClientFactory, parse_sse

_SCRIPT: dict[type, Any] = {
    IntentExtraction: IntentExtraction(
        normalized_query="passport renewal",
        service_guess="passport_renewal",
        entities=IntentEntities(district="Colombo"),
    ),
    ActionSteps: ActionSteps(steps=["Bring your birth certificate"]),
}


def _ask(client: Any, session_id: str) -> list[tuple[str, dict[str, Any]]]:
    response = client.post(
        "/api/chat", json={"message": "renew my passport", "session_id": session_id}
    )
    assert response.status_code == 200
    return parse_sse(response.text)


def _pills(events: list[tuple[str, dict[str, Any]]]) -> set[str]:
    return {data["id"] for event, data in events if event == "step"}


def _pack(events: list[tuple[str, dict[str, Any]]]) -> dict[str, Any] | None:
    packs = [data for event, data in events if event == "action_pack"]
    return packs[0] if packs else None


def test_second_identical_question_is_served_from_cache(
    build_client: ClientFactory,
) -> None:
    client, _ = build_client(_SCRIPT)

    first = _ask(client, "s1")
    second = _ask(client, "s2")  # same service+variant+district, new thread

    assert "lookup" in _pills(first), "the first run must actually retrieve + grade"
    assert "lookup" not in _pills(second), "the second run should skip A4→A5→A6"
    assert _pack(second) == _pack(first) is not None


def test_a_cache_hit_still_completes_the_stream(build_client: ClientFactory) -> None:
    client, _ = build_client(_SCRIPT)
    _ask(client, "s1")

    events = _ask(client, "s2")
    names = [event for event, _ in events]

    assert "action_pack" in names
    assert names[-1] == "done"
    assert any(
        data["id"] == "prepare" and data["status"] == "done"
        for event, data in events
        if event == "step"
    )


def test_the_action_pack_fetch_works_after_a_cache_hit(
    build_client: ClientFactory,
) -> None:
    """A hit must leave the same state behind, so GET action-pack still resolves."""
    client, _ = build_client(_SCRIPT)
    _ask(client, "s1")
    _ask(client, "s2")

    response = client.get("/api/sessions/s2/action-pack")

    assert response.status_code == 200
    assert response.json()["service_label"] == "Passport Renewal"


def test_moderation_invalidates_the_cache(build_client: ClientFactory) -> None:
    """Promoting a source changes the trust label, so cached packs must be dropped."""
    client, _ = build_client(_SCRIPT)
    _ask(client, "s1")
    assert "lookup" not in _pills(_ask(client, "s2")), "expected a warm cache"

    # Source 1 is the seed catalog's only source — the one backing the pack above.
    assert client.post("/api/moderation/1/promote").status_code == 200

    assert "lookup" in _pills(_ask(client, "s3")), "the cache should be cold again"
