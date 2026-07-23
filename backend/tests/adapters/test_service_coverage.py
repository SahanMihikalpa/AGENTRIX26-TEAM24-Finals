"""Service coverage — the signal that stops thin crawl entries winning A2.

The crawl creates a catalog row per web page, so a query like "amendment of NIC"
matches a bare "Amendment of NIC" entry exactly as well as the curated NIC service
that already covers it as a variant. Coverage is how the two are told apart.
"""

from __future__ import annotations

from typing import Any

from app.adapters.knowledge.chroma_sqlite import ChromaSqliteStore
from app.adapters.knowledge.seed import KnowledgeSeeder
from app.domain.entities import ServiceCoverage
from tests.adapters.conftest import DeterministicEmbedder

_SEED: dict[str, Any] = {
    "sources": [
        {
            "key": "src",
            "title": "Circular",
            "url": "https://x.gov.lk",
            "source_type": "circular",
            "retrieved_date": "2026-06-20",
            "confidence": 0.9,
            "verification_status": "verified",
        }
    ],
    "services": [
        {
            # The curated parent: covers amendment as a variant, with real facts.
            "name_en": "National Identity Card (NIC) Issuance",
            "slug": "nic-issuance",
            "category": "identity",
            "description": "Apply for or amend a National Identity Card",
            "variants": [
                {
                    "condition_label": "amendment",
                    "description": "",
                    "requirements": [
                        {"source_key": "src", "document_name": "Birth certificate"},
                        {"source_key": "src", "document_name": "Affidavit"},
                    ],
                    "fees": [{"source_key": "src", "label": "Fee", "amount_lkr": "200"}],
                }
            ],
            "offices": [
                {
                    "name": "DRP Head Office",
                    "office_type": "DRP",
                    "district": "Colombo",
                    "address": "Battaramulla",
                    "hours": "9-4",
                    "contact": "011",
                }
            ],
        },
        {
            # The thin duplicate the crawl produced: name matches, nothing behind it.
            "name_en": "Amendment of NIC",
            "slug": "amendment_of_nic",
            "category": "",
            "description": "",
            "variants": [{"condition_label": "standard", "description": ""}],
        },
    ],
}


def _seeded(store: ChromaSqliteStore) -> ChromaSqliteStore:
    KnowledgeSeeder(store, DeterministicEmbedder()).load(_SEED)
    return store


def test_coverage_counts_the_facts_behind_a_service(store: ChromaSqliteStore) -> None:
    _seeded(store)
    parent = next(s for s in store.find_services("nic-issuance") if s.slug == "nic-issuance")
    assert parent.id is not None

    coverage = store.get_service_coverage([parent.id])[parent.id]

    assert coverage == ServiceCoverage(requirements=2, fees=1, offices=1)
    assert coverage.is_answerable


def test_a_thin_service_reports_zero_coverage(store: ChromaSqliteStore) -> None:
    _seeded(store)
    thin = next(s for s in store.find_services("amendment_of_nic") if s.slug == "amendment_of_nic")
    assert thin.id is not None

    coverage = store.get_service_coverage([thin.id])[thin.id]

    assert coverage == ServiceCoverage()
    assert not coverage.is_answerable


def test_unknown_ids_come_back_zeroed_not_missing(store: ChromaSqliteStore) -> None:
    coverage = store.get_service_coverage([999, 998])

    assert coverage == {999: ServiceCoverage(), 998: ServiceCoverage()}


def test_empty_input_is_handled(store: ChromaSqliteStore) -> None:
    assert store.get_service_coverage([]) == {}


def test_coverage_breaks_a_tie_towards_the_answerable_service(
    store: ChromaSqliteStore,
) -> None:
    """On equal keyword scores, the service that can actually answer goes first.

    "nic" matches one token in each row, so lexical scoring alone leaves the order
    to insertion chance — and picking the bare duplicate leaves A6 with nothing to
    build a checklist from.
    """
    _seeded(store)

    ranked = [s.slug for s in store.find_services("nic")]

    assert ranked[0] == "nic-issuance", ranked


def test_coverage_never_overrides_a_better_keyword_match(
    store: ChromaSqliteStore,
) -> None:
    """Coverage is a tie-break, not a thumb on the scale.

    A service that genuinely matches more of the query must still win even with
    nothing documented — otherwise the gap loop could never route to a new service,
    and acquiring knowledge is the whole point of the B-team. This is also why the
    tie-break alone does not fix the duplicate problem: "amendment of my NIC" hits
    the thin row *twice* and the curated one once, so the fix that matters is the
    coverage annotation A2 hands to the LLM (see test_a2_identify).
    """
    _seeded(store)

    ranked = store.find_services("amendment of my NIC")

    assert ranked[0].slug == "amendment_of_nic", [s.slug for s in ranked]
    assert "nic-issuance" in [s.slug for s in ranked], "both stay candidates for A2"
