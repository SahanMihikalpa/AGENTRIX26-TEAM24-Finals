"""B2 · Extract & Curate — raw evidence → provenanced, validated records."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.application.agents.b2_curate import ExtractCurateAgent
from app.application.agents.schemas import CuratedExtraction, CuratedRequirement
from app.application.graph.state import GraphState, new_state
from tests.application.conftest import ScriptedLLM


def _state(*entries: dict[str, Any]) -> GraphState:
    state = new_state("s", "register a business name")
    state["acquisition_buffer"] = list(entries)
    return state


def _entry(origin: str = "pool", *, official: bool = True) -> dict[str, Any]:
    return {
        "text": "business name registration needs an NIC copy; fee LKR 2000",
        "title": "Business Reg Circular",
        "url": "https://doc.gov.lk/biz",
        "source_type": "circular",
        "published_date": None,
        "origin": origin,
        "official": official,
    }


def _extraction(service: str = "Business Name Registration") -> CuratedExtraction:
    return CuratedExtraction(
        service_name=service,
        service_slug="business_name_registration" if service else "",
        requirements=[CuratedRequirement(document_name="NIC copy")],
        extraction_confidence=0.9,
    )


def test_curates_with_provenance_and_authority_weighted_confidence() -> None:
    llm = ScriptedLLM(structured={CuratedExtraction: _extraction()})
    agent = ExtractCurateAgent(llm, today=date(2026, 6, 21))

    curated = agent(_state(_entry("pool")))["curated"]

    assert len(curated) == 1
    record = curated[0]
    assert record["source"]["verification_status"] == "auto_gathered"
    assert record["source"]["retrieved_date"] == "2026-06-21"
    assert record["source"]["confidence"] == 0.72  # 0.8 authority * 0.9 certainty
    assert record["extraction"]["service_slug"] == "business_name_registration"
    assert record["text"].startswith("business name registration")


def test_web_origin_is_trusted_less_than_pool() -> None:
    llm = ScriptedLLM(structured={CuratedExtraction: _extraction()})
    agent = ExtractCurateAgent(llm, today=date(2026, 6, 21))

    curated = agent(_state(_entry("web")))["curated"]

    # Official web: 0.75 authority * 0.9 certainty = 0.675 — below the pool (0.72)
    # but above the serving gate (τ=0.6), so an official gov.lk find can be served.
    assert curated[0]["source"]["confidence"] == 0.675


def test_unofficial_web_is_trusted_less_than_official_and_stays_below_the_gate() -> None:
    llm = ScriptedLLM(structured={CuratedExtraction: _extraction()})
    agent = ExtractCurateAgent(llm, today=date(2026, 6, 21))

    official = agent(_state(_entry("web", official=True)))["curated"][0]
    unofficial = agent(_state(_entry("web", official=False)))["curated"][0]

    assert official["source"]["confidence"] == 0.675
    assert unofficial["source"]["confidence"] == 0.45  # 0.5 * 0.9 — gated to review
    assert unofficial["source"]["confidence"] < 0.6


def test_unmappable_extraction_is_dropped() -> None:
    llm = ScriptedLLM(structured={CuratedExtraction: _extraction(service="")})
    agent = ExtractCurateAgent(llm)

    curated = agent(_state(_entry()))["curated"]

    assert curated == []  # no identifiable service → nothing to write
