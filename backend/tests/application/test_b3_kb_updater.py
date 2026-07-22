"""B3 · KB-Updater — dedup + structured write + embed/upsert (self-expansion)."""

from __future__ import annotations

from typing import Any

from app.application.agents.b3_kb_updater import KBUpdaterAgent
from app.application.graph.state import GraphState, new_state
from app.domain.entities import Service
from tests.application.conftest import DeterministicEmbedder, SeededKB


def _service_by_slug(kb: SeededKB, slug: str) -> Service:
    return next(s for s in kb.store.find_services(slug) if s.slug == slug)


def _curated(
    *,
    slug: str = "business_name_registration",
    service_name: str = "Business Name Registration",
    url: str = "https://doc.gov.lk/biz",
    condition_label: str = "standard",
    text: str = "business name registration nic copy registration fee colombo",
) -> dict[str, Any]:
    return {
        "source": {
            "title": "Business Reg Circular",
            "url": url,
            "source_type": "circular",
            "published_date": None,
            "retrieved_date": "2026-06-21",
            "confidence": 0.7,
            "verification_status": "auto_gathered",
            "origin": "web",
        },
        "extraction": {
            "service_name": service_name,
            "service_slug": slug,
            "category": "business",
            "description": "Register a business name",
            "condition_label": condition_label,
            "requirements": [{"document_name": "NIC copy", "is_mandatory": True, "notes": ""}],
            "fees": [{"label": "Registration fee", "amount_lkr": "2000", "notes": ""}],
            "offices": [{"name": "DS Colombo", "district": "Colombo", "address": "Town Hall"}],
            "district": "Colombo",
            "district_notes": "",
            "extraction_confidence": 0.7,
        },
        "text": text,
    }


def _state(*records: dict[str, Any]) -> GraphState:
    state = new_state("s", "register a business name")
    state["curated"] = list(records)
    return state


def test_writes_new_service_and_signals_update(
    kb: SeededKB, embedder: DeterministicEmbedder
) -> None:
    agent = KBUpdaterAgent(kb.store, embedder)

    update = agent(_state(_curated()))

    assert update["kb_updated"] is True
    service = _service_by_slug(kb, "business_name_registration")
    assert service.id is not None
    variant = kb.store.list_variants(service.id)[0]
    assert variant.id is not None
    assert [r.document_name for r in kb.store.get_requirements(variant.id)] == ["NIC copy"]
    assert str(kb.store.get_fees(variant.id)[0].amount_lkr) == "2000"
    # the handling office was linked to the new service
    assert kb.store.get_offices(service.id, district="Colombo")[0].name == "DS Colombo"


def test_dedup_is_idempotent(kb: SeededKB, embedder: DeterministicEmbedder) -> None:
    agent = KBUpdaterAgent(kb.store, embedder)
    record = _curated()

    first = agent(_state(record))
    second = agent(_state(record))  # same url + content hash

    assert first["kb_updated"] is True
    assert second["kb_updated"] is False  # nothing re-ingested
    service = _service_by_slug(kb, "business_name_registration")
    assert service.id is not None
    variant = kb.store.list_variants(service.id)[0]
    assert variant.id is not None
    assert len(kb.store.get_requirements(variant.id)) == 1  # not doubled


def test_hands_service_id_back_when_filling_unknown_gap(
    kb: SeededKB, embedder: DeterministicEmbedder
) -> None:
    agent = KBUpdaterAgent(kb.store, embedder)
    state = _state(_curated())
    state["service_unknown"] = True  # we were filling an unknown-service gap

    update = agent(state)

    # B3 hands the freshly-created service back so A4 can re-retrieve and converge
    assert update["service_unknown"] is False
    service = _service_by_slug(kb, "business_name_registration")
    assert update["service_id"] == service.id


def test_does_not_override_service_id_for_known_gap(
    kb: SeededKB, embedder: DeterministicEmbedder
) -> None:
    agent = KBUpdaterAgent(kb.store, embedder)

    update = agent(_state(_curated()))  # service_unknown defaults False

    assert "service_id" not in update  # a known-service gap keeps its existing id
    assert "service_unknown" not in update


def test_reuses_existing_service_adds_new_variant(
    kb: SeededKB, embedder: DeterministicEmbedder
) -> None:
    agent = KBUpdaterAgent(kb.store, embedder)
    # curate against the already-seeded service, with a brand-new "gift" variant
    record = _curated(
        slug="land_deed_transfer",
        service_name="Land Deed Transfer",
        url="https://doc.gov.lk/gift",
        condition_label="gift",
        text="land deed transfer by gift requires a notarised gift deed",
    )

    update = agent(_state(record))

    assert update["kb_updated"] is True
    labels = {v.condition_label for v in kb.store.list_variants(kb.deed_service_id)}
    assert labels == {"inheritance", "sale", "gift"}  # reused service, appended variant
