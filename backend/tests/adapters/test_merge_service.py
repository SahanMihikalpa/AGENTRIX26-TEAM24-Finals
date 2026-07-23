"""Merging a thin duplicate catalog entry into the curated service it duplicates."""

from __future__ import annotations

from typing import Any

import pytest

from app.adapters.knowledge.chroma_sqlite import ChromaSqliteStore
from app.adapters.knowledge.seed import KnowledgeSeeder
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
            "name_en": "National Identity Card (NIC) Issuance",
            "slug": "nic-issuance",
            "category": "identity",
            "description": "Apply for or amend a National Identity Card",
            "variants": [
                {
                    "condition_label": "amendment",
                    "description": "",
                    "requirements": [
                        {"source_key": "src", "document_name": "Birth certificate"}
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
            "chunks": [{"source_key": "src", "content": "nic issuance amendment colombo"}],
        },
        {
            "name_en": "Amendment of NIC",
            "slug": "amendment_of_nic",
            "category": "",
            "description": "",
            "variants": [
                {
                    "condition_label": "standard",
                    "description": "",
                    "requirements": [
                        {"source_key": "src", "document_name": "Some scraped document"}
                    ],
                }
            ],
            "offices": [
                {
                    "name": "Kandy DS",
                    "office_type": "DS",
                    "district": "Kandy",
                    "address": "Kandy",
                    "hours": "9-4",
                    "contact": "081",
                }
            ],
            "chunks": [{"source_key": "src", "content": "amendment of nic scraped page text"}],
        },
    ],
}


@pytest.fixture
def kb(store: ChromaSqliteStore) -> tuple[ChromaSqliteStore, int, int]:
    KnowledgeSeeder(store, DeterministicEmbedder()).load(_SEED)
    parent = next(s for s in store.find_services("nic-issuance") if s.slug == "nic-issuance")
    dupe = next(
        s for s in store.find_services("amendment_of_nic") if s.slug == "amendment_of_nic"
    )
    assert parent.id is not None and dupe.id is not None
    return store, parent.id, dupe.id


def _count(store: ChromaSqliteStore, sql: str, *params: object) -> int:
    return int(store._conn.execute(sql, params).fetchone()[0])


def test_dry_run_reports_without_changing_anything(
    kb: tuple[ChromaSqliteStore, int, int],
) -> None:
    store, parent_id, dupe_id = kb

    outcome = store.merge_service(dupe_id, parent_id, dry_run=True)

    assert outcome is not None
    assert outcome.duplicate_id == dupe_id and outcome.parent_id == parent_id
    assert outcome.chunks_moved == 1
    assert outcome.variants_dropped == 1
    assert outcome.requirements_dropped == 1
    assert outcome.offices_relinked == 1
    assert store.get_service(dupe_id) is not None, "dry run must not delete"


def test_merge_moves_chunks_and_retires_the_duplicate(
    kb: tuple[ChromaSqliteStore, int, int],
) -> None:
    store, parent_id, dupe_id = kb

    store.merge_service(dupe_id, parent_id)

    assert store.get_service(dupe_id) is None
    assert _count(store, "SELECT COUNT(*) FROM kb_chunk WHERE service_id = ?", dupe_id) == 0
    # The crawled text is kept, not deleted — it is the part with retrieval value.
    assert _count(store, "SELECT COUNT(*) FROM kb_chunk WHERE service_id = ?", parent_id) == 2


def test_merge_keeps_the_parents_curated_facts(
    kb: tuple[ChromaSqliteStore, int, int],
) -> None:
    store, parent_id, dupe_id = kb
    before = store.get_service_coverage([parent_id])[parent_id]

    store.merge_service(dupe_id, parent_id)
    after = store.get_service_coverage([parent_id])[parent_id]

    assert after.requirements == before.requirements, "curated facts untouched"
    assert after.fees == before.fees
    assert after.offices == before.offices + 1, "the duplicate's office is inherited"


def test_merge_discards_the_duplicates_thin_variants(
    kb: tuple[ChromaSqliteStore, int, int],
) -> None:
    store, parent_id, dupe_id = kb
    variant_id = int(
        store._conn.execute(
            "SELECT id FROM service_variant WHERE service_id = ?", (dupe_id,)
        ).fetchone()[0]
    )

    store.merge_service(dupe_id, parent_id)

    assert _count(store, "SELECT COUNT(*) FROM service_variant WHERE id = ?", variant_id) == 0
    assert _count(store, "SELECT COUNT(*) FROM requirement WHERE variant_id = ?", variant_id) == 0
    assert len(store.list_variants(parent_id)) == 1, "parent keeps only its own variants"


def test_the_merged_chunk_is_retrievable_under_the_parent(
    kb: tuple[ChromaSqliteStore, int, int],
) -> None:
    """Chroma carries its own service_id; if it is not updated the chunk is lost."""
    store, parent_id, dupe_id = kb
    embedder = DeterministicEmbedder()

    store.merge_service(dupe_id, parent_id)
    hits = store.search(
        embedder.embed_query("scraped page text"),
        filters={"service_id": parent_id},
        top_k=5,
    )

    assert any("scraped page text" in hit.content for hit in hits), [h.content for h in hits]


def test_unknown_or_self_merge_is_refused(kb: tuple[ChromaSqliteStore, int, int]) -> None:
    store, parent_id, dupe_id = kb

    assert store.merge_service(9999, parent_id) is None
    assert store.merge_service(dupe_id, 9999) is None
    assert store.merge_service(parent_id, parent_id) is None
    assert store.get_service(dupe_id) is not None, "nothing was touched"
