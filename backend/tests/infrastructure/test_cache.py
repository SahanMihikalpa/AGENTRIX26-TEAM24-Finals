"""Unit tests for the in-memory query→answer cache (AD-12)."""

from __future__ import annotations

from typing import Any

from app.infrastructure.cache import InMemoryAnswerCache


def _answer(label: str) -> dict[str, Any]:
    return {"service_label": label}


def test_put_get_roundtrip() -> None:
    cache = InMemoryAnswerCache()
    cache.put_answer(1, _answer("NIC"), variant_id=2, district="Colombo")
    assert cache.get_answer(1, variant_id=2, district="Colombo") == _answer("NIC")


def test_missing_key_returns_none() -> None:
    assert InMemoryAnswerCache().get_answer(99) is None


def test_district_is_normalized_for_lookup() -> None:
    cache = InMemoryAnswerCache()
    cache.put_answer(1, _answer("a"), district="Colombo")
    assert cache.get_answer(1, district="  colombo ") is not None


def test_variant_and_district_are_part_of_the_key() -> None:
    cache = InMemoryAnswerCache()
    cache.put_answer(1, _answer("a"), variant_id=2, district="Colombo")
    assert cache.get_answer(1, variant_id=3, district="Colombo") is None
    assert cache.get_answer(1, variant_id=2, district="Kandy") is None


def test_invalidate_service_drops_only_that_service() -> None:
    cache = InMemoryAnswerCache()
    cache.put_answer(1, _answer("a"), variant_id=1)
    cache.put_answer(1, _answer("b"), variant_id=2)
    cache.put_answer(2, _answer("c"))

    cache.invalidate_service(1)

    assert cache.get_answer(1, variant_id=1) is None
    assert cache.get_answer(1, variant_id=2) is None
    assert cache.get_answer(2) is not None


def test_lru_eviction_respects_maxsize() -> None:
    cache = InMemoryAnswerCache(maxsize=2)
    cache.put_answer(1, _answer("a"))
    cache.put_answer(2, _answer("b"))
    cache.get_answer(1)  # touch 1 → 2 becomes least-recently-used
    cache.put_answer(3, _answer("c"))  # evicts 2

    assert cache.get_answer(2) is None
    assert cache.get_answer(1) is not None
    assert cache.get_answer(3) is not None
    assert len(cache) == 2
