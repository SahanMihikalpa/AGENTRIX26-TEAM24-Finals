"""A6 · Action-Pack Generator — grounded assembly + the confidence serving gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.adapters.knowledge.chroma_sqlite import ChromaSqliteStore
from app.adapters.knowledge.seed import KnowledgeSeeder
from app.application.agents.a6_action_pack import ActionPackAgent
from app.application.agents.schemas import ActionSteps
from app.application.graph.state import GraphState, new_state
from tests.application.conftest import DeterministicEmbedder, ScriptedLLM, SeededKB


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
    # Citations name the sources behind the rows shown, matching the UI's promise
    # that "every requirement above is based on these official sources".
    assert answer["citations"][0]["source_id"] == answer["documents"][0]["source_id"]
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


def test_unknown_service_fallback_omits_office_and_cross_service_citations(kb: SeededKB) -> None:
    # PAYE-style: the service is not in the catalog, but A4 still returned the closest
    # (unrelated, verified) seed chunks. The fallback must not cite them, must not
    # promise an office that doesn't exist, and must not claim a verified answer.
    state = _state(kb, grade="GAP")
    state["service_id"] = None
    state["variant_id"] = None

    answer = ActionPackAgent(kb.store)(state)["answer"]

    assert answer is not None
    assert answer["fallback"] is True
    assert answer["service_label"] == "Your request"
    assert answer["office"] is None
    assert answer["citations"] == []
    assert answer["verification"] == "newly_gathered_pending_verification"
    assert "office below" not in answer["fallback_message"]
    assert "office below" not in answer["steps"][0]


# ── the confidence gate, exercised through the facts' own provenance ──
#
# The gate judges the sources behind the documents and fees A6 renders, not the
# chunks retrieval happened to return. These build a tiny catalog whose facts come
# from a source of a chosen confidence/status, so each case is set up honestly
# rather than by dressing up the retrieval payload.
def _kb_backed_by(
    tmp_path: Path, *, confidence: float, status: str
) -> tuple[ChromaSqliteStore, int, int]:
    seed: dict[str, Any] = {
        "sources": [
            {
                "key": "backing",
                "title": "Source behind the facts",
                "url": "https://x.gov.lk",
                "source_type": "portal",
                "retrieved_date": "2026-06-20",
                "confidence": confidence,
                "verification_status": status,
            }
        ],
        "services": [
            {
                "name_en": "Boundary Correction",
                "slug": "boundary-correction",
                "category": "land",
                "description": "Correct a land boundary",
                "variants": [
                    {
                        "condition_label": "standard",
                        "description": "",
                        "requirements": [
                            {"source_key": "backing", "document_name": "Survey plan"}
                        ],
                        "fees": [
                            {"source_key": "backing", "label": "Fee", "amount_lkr": "500"}
                        ],
                    }
                ],
            }
        ],
    }
    store = ChromaSqliteStore(sqlite_path=tmp_path / "kb.sqlite3", chroma_dir=tmp_path / "chroma")
    KnowledgeSeeder(store, DeterministicEmbedder()).load(seed)
    service = store.find_services("boundary-correction")[0]
    assert service.id is not None
    variant = store.list_variants(service.id)[0]
    assert variant.id is not None
    return store, service.id, variant.id


def _state_for(store_ids: tuple[ChromaSqliteStore, int, int], **kwargs: Any) -> GraphState:
    _, service_id, variant_id = store_ids
    state = new_state("s", "correct my boundary")
    state["service_id"] = service_id
    state["variant_id"] = variant_id
    state["slots"] = {"district": "Galle"}
    state["grade"] = "SUFFICIENT"
    state["answer_confidence"] = kwargs.get("confidence", 0.95)
    state["retrieved"] = kwargs.get("retrieved", _retrieved())
    return state


def test_gate_blocks_facts_from_a_low_confidence_unverified_source(tmp_path: Path) -> None:
    """The guardrail itself: unverified facts below the threshold are never served."""
    kb = _kb_backed_by(tmp_path, confidence=0.4, status="auto_gathered")

    answer = ActionPackAgent(kb[0], confidence_threshold=0.6)(_state_for(kb))["answer"]

    assert answer is not None
    assert answer["fallback"] is True
    assert answer["documents"] == []


def test_gate_serves_unverified_facts_that_clear_the_threshold(tmp_path: Path) -> None:
    kb = _kb_backed_by(tmp_path, confidence=0.9, status="auto_gathered")

    answer = ActionPackAgent(kb[0], confidence_threshold=0.6)(_state_for(kb))["answer"]

    assert answer is not None
    assert answer["fallback"] is False
    assert answer["verification"] == "newly_gathered_pending_verification"


def test_verified_facts_bypass_the_confidence_threshold(tmp_path: Path) -> None:
    kb = _kb_backed_by(tmp_path, confidence=0.1, status="verified")

    answer = ActionPackAgent(kb[0], confidence_threshold=0.6)(_state_for(kb))["answer"]

    assert answer is not None
    assert answer["fallback"] is False
    assert answer["verification"] == "verified"


def test_a_weak_retrieved_chunk_does_not_suppress_verified_facts(kb: SeededKB) -> None:
    """The regression this change exists for.

    Retrieval can surface a low-confidence crawled chunk that contributed nothing
    to the answer — after a service merge, routinely. Judging the pack on that
    chunk suppressed checklists assembled entirely from verified rows.
    """
    state = _state(kb, confidence=0.3, retrieved=_retrieved(status="auto_gathered", confidence=0.3))

    answer = ActionPackAgent(kb.store, confidence_threshold=0.6)(state)["answer"]

    assert answer is not None
    assert answer["fallback"] is False, "verified rows must still be served"
    assert [doc["name"] for doc in answer["documents"]] == ["Death certificate"]
    assert answer["verification"] == "verified"


def test_a_variant_with_no_sourced_rows_is_refused(kb: SeededKB) -> None:
    """New, stricter: an empty checklist must never go out wearing a badge.

    The old gate looked only at retrieval, so a variant with nothing behind it
    produced a pack with zero documents and a "verified" label.
    """
    state = _state(kb)
    state["service_id"] = kb.survey_service_id  # seeded with no requirements or fees
    state["variant_id"] = kb.survey_variant_id

    answer = ActionPackAgent(kb.store, confidence_threshold=0.6)(state)["answer"]

    assert answer is not None
    assert answer["fallback"] is True
    assert answer["documents"] == []


def test_llm_sequences_the_steps_when_available(kb: SeededKB) -> None:
    steps = ActionSteps(steps=["Gather the death certificate.", "Visit DS Galle.", "Pay LKR 1000."])
    agent = ActionPackAgent(kb.store, ScriptedLLM(structured={ActionSteps: steps}))

    answer = agent(_state(kb))["answer"]

    assert answer is not None
    assert answer["steps"] == ["Gather the death certificate.", "Visit DS Galle.", "Pay LKR 1000."]
