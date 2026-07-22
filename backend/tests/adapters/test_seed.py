"""Tests for the knowledge seeder."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from app.adapters.knowledge.chroma_sqlite import ChromaSqliteStore
from app.adapters.knowledge.seed import KnowledgeSeeder, validate_catalog

_CATALOG: dict[str, Any] = {
    "sources": [
        {
            "key": "src1",
            "title": "NIC Circular 2025",
            "url": "https://drp.gov.lk/c1",
            "source_type": "circular",
            "retrieved_date": "2026-06-20",
            "confidence": 1.0,
            "verification_status": "verified",
        }
    ],
    "services": [
        {
            "slug": "nic_renewal",
            "name_en": "NIC Renewal",
            "category": "identity",
            "description": "Renew NIC",
            "variants": [
                {
                    "condition_label": "standard",
                    "description": "Standard renewal",
                    "requirements": [
                        {"document_name": "Old NIC", "is_mandatory": True, "source_key": "src1"}
                    ],
                    "fees": [{"label": "Service fee", "amount_lkr": "100", "source_key": "src1"}],
                }
            ],
            "offices": [
                {
                    "name": "DRP Colombo",
                    "office_type": "DRP",
                    "district": "Colombo",
                    "address": "Main",
                    "hours": "9-4",
                    "contact": "011",
                }
            ],
            "district_variations": [
                {"district": "Jaffna", "source_key": "src1", "notes": "extra GS letter"}
            ],
            "chunks": [
                {
                    "content": "NIC renewal requires the old NIC and a recent photo",
                    "source_key": "src1",
                    "chunk_index": 0,
                }
            ],
        }
    ],
}


def test_seed_loads_full_catalog(store: ChromaSqliteStore, embedder) -> None:
    stats = KnowledgeSeeder(store, embedder).load(_CATALOG)

    assert stats.sources == 1
    assert stats.services == 1
    assert stats.variants == 1
    assert stats.requirements == 1
    assert stats.fees == 1
    assert stats.offices == 1
    assert stats.district_variations == 1
    assert stats.chunks == 1

    assert store.find_services("NIC")[0].slug == "nic_renewal"
    results = store.search(embedder.embed_query("old NIC photo"))
    assert results
    assert results[0].source.id is not None


def test_seed_from_json_file(tmp_path: Path, store: ChromaSqliteStore, embedder) -> None:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(_CATALOG), encoding="utf-8")
    stats = KnowledgeSeeder(store, embedder).load_from_json(path)
    assert stats.chunks == 1


# ── catalog validation ───────────────────────────────────────────
_VALID: dict[str, Any] = {
    "sources": [
        {
            "key": "s1",
            "title": "Source One",
            "source_type": "circular",
            "retrieved_date": "2026-06-20",
            "verification_status": "verified",
        }
    ],
    "services": [
        {
            "slug": "svc",
            "name_en": "Service",
            "category": "Land & Property",
            "description": "",
            "variants": [
                {
                    "condition_label": "standard",
                    "requirements": [{"document_name": "Deed", "source_key": "s1"}],
                    "fees": [{"label": "Fee", "amount_lkr": "1000.00", "source_key": "s1"}],
                }
            ],
            "offices": [{"name": "Office", "office_type": "other", "district": "Colombo"}],
            "chunks": [{"content": "some text", "source_key": "s1"}],
        }
    ],
}


def test_validate_catalog_accepts_valid_catalog() -> None:
    assert validate_catalog(_VALID) == []


def test_validate_catalog_flags_unknown_source_key() -> None:
    bad = copy.deepcopy(_VALID)
    bad["services"][0]["variants"][0]["fees"][0]["source_key"] = "ghost"
    problems = validate_catalog(bad)
    assert any("unknown source_key 'ghost'" in p for p in problems)


def test_validate_catalog_enforces_category_vocabulary_only_when_checked() -> None:
    bad = copy.deepcopy(_VALID)
    bad["services"][0]["category"] = "made-up"
    assert any("unknown category" in p for p in validate_catalog(bad))
    # the load path validates integrity only, so a free-form category is allowed there
    assert validate_catalog(bad, check_category=False) == []


def test_validate_catalog_flags_bad_decimal_and_enum() -> None:
    bad = copy.deepcopy(_VALID)
    bad["services"][0]["variants"][0]["fees"][0]["amount_lkr"] = "free"
    bad["sources"][0]["source_type"] = "tabloid"
    problems = validate_catalog(bad)
    assert any("not a valid decimal" in p for p in problems)
    assert any("invalid source_type" in p for p in problems)


def test_seed_load_rejects_unknown_source_key(store: ChromaSqliteStore, embedder) -> None:
    bad = copy.deepcopy(_VALID)
    bad["services"][0]["chunks"][0]["source_key"] = "ghost"
    with pytest.raises(ValueError, match="unknown source_key"):
        KnowledgeSeeder(store, embedder).load(bad)
