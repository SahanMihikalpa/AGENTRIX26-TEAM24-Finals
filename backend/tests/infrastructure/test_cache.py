"""Unit tests for the in-memory query→answer cache (AD-12).

The cached value is the **serialized** Action Pack — the same dict that lives in
``GraphState["answer"]`` — so the packs here go through ``action_pack_to_state``
rather than being stored as entities.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.application.graph.serialization import action_pack_to_state
from app.domain.entities import ActionPack, ActionPackVerification
from app.domain.ports.cache import CacheKey
from app.infrastructure.cache import InMemoryAnswerCache


def _pack(label: str) -> dict[str, Any]:
    return action_pack_to_state(
        ActionPack(
            service_label=label,
            district=None,
            documents=(),
            fees=(),
            office=None,
            steps=(),
            estimated_cost_lkr=Decimal("0"),
            verification=ActionPackVerification.VERIFIED,
            citations=(),
        )
    )


def test_put_get_roundtrip() -> None:
    cache = InMemoryAnswerCache()
    key = CacheKey.build(1, variant_id=2, district="Colombo")
    pack = _pack("NIC")
    cache.put(key, pack)
    assert cache.get(key) == pack


def test_missing_key_returns_none() -> None:
    assert InMemoryAnswerCache().get(CacheKey.build(99)) is None


def test_district_is_normalized_for_lookup() -> None:
    cache = InMemoryAnswerCache()
    cache.put(CacheKey.build(1, district="Colombo"), _pack("a"))
    assert cache.get(CacheKey.build(1, district="  colombo ")) is not None


def test_variant_and_district_are_part_of_the_identity() -> None:
    cache = InMemoryAnswerCache()
    cache.put(CacheKey.build(1, variant_id=1, district="Colombo"), _pack("a"))

    assert cache.get(CacheKey.build(1, variant_id=2, district="Colombo")) is None
    assert cache.get(CacheKey.build(1, variant_id=1, district="Galle")) is None
    assert cache.get(CacheKey.build(1, variant_id=1)) is None


def test_invalidate_service_drops_only_that_service() -> None:
    cache = InMemoryAnswerCache()
    cache.put(CacheKey.build(1, variant_id=1), _pack("a"))
    cache.put(CacheKey.build(1, variant_id=2), _pack("b"))
    cache.put(CacheKey.build(2), _pack("c"))

    cache.invalidate_service(1)

    assert cache.get(CacheKey.build(1, variant_id=1)) is None
    assert cache.get(CacheKey.build(1, variant_id=2)) is None
    assert cache.get(CacheKey.build(2)) is not None


def test_clear_drops_everything() -> None:
    cache = InMemoryAnswerCache()
    cache.put(CacheKey.build(1), _pack("a"))
    cache.put(CacheKey.build(2), _pack("b"))

    cache.clear()

    assert len(cache) == 0


def test_lru_eviction_respects_maxsize() -> None:
    cache = InMemoryAnswerCache(maxsize=2)
    cache.put(CacheKey.build(1), _pack("a"))
    cache.put(CacheKey.build(2), _pack("b"))
    cache.get(CacheKey.build(1))  # touch 1 → 2 becomes least-recently-used
    cache.put(CacheKey.build(3), _pack("c"))  # evicts 2

    assert cache.get(CacheKey.build(2)) is None
    assert cache.get(CacheKey.build(1)) is not None
    assert cache.get(CacheKey.build(3)) is not None
    assert len(cache) == 2
