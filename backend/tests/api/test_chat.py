"""``POST /api/chat`` SSE + the Action-Pack fetch, driven end-to-end."""

from __future__ import annotations

from typing import Any

from app.application.agents.schemas import (
    ActionSteps,
    ClarificationQuestion,
    CuratedExtraction,
    CuratedFee,
    CuratedRequirement,
    IntentEntities,
    IntentExtraction,
)
from app.domain.entities import SourceType
from app.domain.ports.source_pool import PooledDocument
from app.infrastructure.cache import InMemoryAnswerCache
from tests.api.conftest import ClientFactory, parse_sse


def _of(events: list[tuple[str, dict[str, Any]]], name: str) -> list[dict[str, Any]]:
    return [data for event, data in events if event == name]


def test_happy_path_streams_steps_and_action_pack(build_client: ClientFactory) -> None:
    client, _ = build_client(
        {
            IntentExtraction: IntentExtraction(
                normalized_query="passport renewal",
                service_guess="passport_renewal",
                entities=IntentEntities(district="Colombo"),
            ),
            ActionSteps: ActionSteps(steps=["Bring your birth certificate"]),
        }
    )

    response = client.post("/api/chat", json={"message": "renew my passport", "session_id": "s1"})

    assert response.status_code == 200
    events = parse_sse(response.text)
    names = [event for event, _ in events]
    assert "clarify" not in names
    assert names[-1] == "done"

    packs = _of(events, "action_pack")
    assert len(packs) == 1
    assert packs[0]["service_label"] == "Passport Renewal"
    assert [doc["name"] for doc in packs[0]["documents"]] == ["Birth certificate"]
    assert packs[0]["fees"][0]["amount_lkr"] == 3000.0  # number on the wire, not "3000"
    assert any(s["id"] == "prepare" and s["status"] == "done" for s in _of(events, "step"))


def test_clarify_pauses_then_resume_answers(build_client: ClientFactory) -> None:
    client, _ = build_client(
        {
            IntentExtraction: IntentExtraction(
                normalized_query="land deed transfer",
                service_guess="land_deed_transfer",
                entities=IntentEntities(district="Galle"),  # only the variant is unknown
            ),
            ClarificationQuestion: ClarificationQuestion(question="Inheritance, sale, or gift?"),
            ActionSteps: ActionSteps(steps=["Collect documents"]),
        }
    )

    first = parse_sse(
        client.post("/api/chat", json={"message": "transfer my land", "session_id": "s2"}).text
    )
    clarifies = _of(first, "clarify")
    assert len(clarifies) == 1
    assert set(clarifies[0]["options"]) == {"inheritance", "sale"}
    assert not _of(first, "action_pack")  # paused, no pack yet
    assert first[-1][0] == "done"

    second = parse_sse(
        client.post("/api/chat", json={"message": "inheritance", "session_id": "s2"}).text
    )
    packs = _of(second, "action_pack")
    assert len(packs) == 1
    assert packs[0]["service_label"] == "Land Deed Transfer (inheritance)"


def test_gap_loop_streams_gap_events_and_grows_kb(build_client: ClientFactory) -> None:
    pool = [
        PooledDocument(
            text="business name registration nic copy fee colombo",
            title="Business Reg",
            source_type=SourceType.CIRCULAR,
            url="https://reg.gov.lk/biz",
        )
    ]
    client, store = build_client(
        {
            IntentExtraction: IntentExtraction(
                normalized_query="business name registration", service_guess="biz"
            ),
            CuratedExtraction: CuratedExtraction(
                service_name="Business Name Registration",
                service_slug="business_name_registration",
                condition_label="standard",
                requirements=[CuratedRequirement(document_name="NIC copy")],
                fees=[CuratedFee(label="Reg fee", amount_lkr="2000")],
                district="Colombo",
                extraction_confidence=0.9,
            ),
            ActionSteps: ActionSteps(steps=["Bring your NIC"]),
        },
        pool_docs=pool,
    )

    events = parse_sse(
        client.post("/api/chat", json={"message": "register a business", "session_id": "s3"}).text
    )

    phases = [gap["phase"] for gap in _of(events, "gap")]
    assert "researching" in phases and "updated" in phases
    pack = _of(events, "action_pack")[0]
    assert pack["verification"] == "newly_gathered_pending_verification"
    assert [doc["name"] for doc in pack["documents"]] == ["NIC copy"]
    assert any(s.slug == "business_name_registration" for s in store.find_services("business"))


def test_action_pack_fetch_after_run(build_client: ClientFactory) -> None:
    client, _ = build_client(
        {
            IntentExtraction: IntentExtraction(
                normalized_query="passport renewal",
                service_guess="passport_renewal",
                entities=IntentEntities(district="Colombo"),
            ),
            ActionSteps: ActionSteps(steps=["Bring your birth certificate"]),
        }
    )
    client.post("/api/chat", json={"message": "renew passport", "session_id": "s4"})

    found = client.get("/api/sessions/s4/action-pack")
    assert found.status_code == 200
    assert found.json()["service_label"] == "Passport Renewal"

    assert client.get("/api/sessions/unknown/action-pack").status_code == 404


def test_repeat_query_is_served_from_cache(build_client: ClientFactory) -> None:
    cache = InMemoryAnswerCache()
    client, _ = build_client(
        {
            IntentExtraction: IntentExtraction(
                normalized_query="passport renewal",
                service_guess="passport_renewal",
                entities=IntentEntities(district="Colombo"),
            ),
            ActionSteps: ActionSteps(steps=["Bring your birth certificate"]),
        },
        cache=cache,
    )

    first = parse_sse(
        client.post("/api/chat", json={"message": "renew passport", "session_id": "k1"}).text
    )
    # different session, identical resolved request → must hit the shared cache
    second = parse_sse(
        client.post("/api/chat", json={"message": "renew passport", "session_id": "k2"}).text
    )

    assert _of(first, "action_pack") and _of(second, "action_pack")
    assert (
        _of(first, "action_pack")[0]["service_label"]
        == _of(second, "action_pack")[0]["service_label"]
    )
    # the first run retrieved (lookup pill); the cache hit skips A4-A6 (no lookup pill)
    assert "lookup" in {step["id"] for step in _of(first, "step")}
    assert "lookup" not in {step["id"] for step in _of(second, "step")}
    assert len(cache) == 1
