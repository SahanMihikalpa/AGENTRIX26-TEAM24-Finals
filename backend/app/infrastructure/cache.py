"""In-memory query→answer cache (AD-12) — implements the ``AnswerCache`` port.

Identical ``service + variant + district`` requests (and demo re-runs) skip the
whole agent graph and replay the previously generated answer, saving the scarce
LLM quota. The cache is **invalidated per service** whenever B3 upserts new
knowledge for it (and on a moderation promote/reject), so a freshly-expanded or
re-moderated KB never serves a stale answer (AD-12's accepted trade-off, removed).

Storage is a thread-safe **LRU** of the **serialised answer dict** — exactly what
A6 writes to the ``GraphState`` and what the API serves, so no domain⇄transport
round-trip is needed. In-memory satisfies AD-12's goal (short-circuiting repeats
within a running server); cross-restart persistence (the "SQLite table" named in
docs/04) is deferred — see docs/10 for this delta.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CacheKey:
    """The identity of a cached answer: a service, optionally narrowed."""

    service_id: int
    variant_id: int | None = None
    district: str | None = None

    @classmethod
    def build(
        cls, service_id: int, *, variant_id: int | None = None, district: str | None = None
    ) -> CacheKey:
        """Construct a key with a normalized (case/space-insensitive) district."""
        normalized = district.strip().lower() if district else None
        return cls(service_id, variant_id, normalized or None)


class InMemoryAnswerCache:
    """A bounded, thread-safe LRU cache of generated answers (the ``AnswerCache`` port)."""

    def __init__(self, *, maxsize: int = 256) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self._maxsize = maxsize
        self._store: OrderedDict[CacheKey, dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get_answer(
        self,
        service_id: int,
        *,
        variant_id: int | None = None,
        district: str | None = None,
    ) -> dict[str, Any] | None:
        key = CacheKey.build(service_id, variant_id=variant_id, district=district)
        with self._lock:
            answer = self._store.get(key)
            if answer is not None:
                self._store.move_to_end(key)  # mark most-recently-used
            return answer

    def put_answer(
        self,
        service_id: int,
        answer: dict[str, Any],
        *,
        variant_id: int | None = None,
        district: str | None = None,
    ) -> None:
        key = CacheKey.build(service_id, variant_id=variant_id, district=district)
        with self._lock:
            self._store[key] = answer
            self._store.move_to_end(key)
            while len(self._store) > self._maxsize:
                self._store.popitem(last=False)  # evict least-recently-used

    def invalidate_service(self, service_id: int) -> None:
        """Drop every cached answer for ``service_id`` (KB upsert / moderation, AD-12)."""
        with self._lock:
            stale = [key for key in self._store if key.service_id == service_id]
            for key in stale:
                del self._store[key]

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
