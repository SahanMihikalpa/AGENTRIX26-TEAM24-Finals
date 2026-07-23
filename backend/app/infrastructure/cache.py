"""In-memory implementation of the :class:`~app.domain.ports.cache.AnswerCache` port (AD-12).

Identical ``service + variant + district`` queries — and demo re-runs — skip the
A4→A5→A6 tail of the graph and return the previously generated Action Pack,
saving the scarce LLM quota. The cache is **invalidated per service** whenever B3
upserts new knowledge for it, so a freshly-expanded KB never serves a stale
answer (AD-12's accepted trade-off, neutralised).

Storage is **in-memory** (thread-safe LRU). This satisfies AD-12's goal —
short-circuiting repeated queries within a running server (demo re-runs) — without
the premature cost of a durable tier. It also means the cache is per-process: a
multi-replica deployment would need a shared store. Cross-restart persistence (the
"SQLite table" named in docs/04) stays deferred; see docs/10 for this delta.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any

from app.domain.ports.cache import CacheKey

__all__ = ["CacheKey", "InMemoryAnswerCache"]


class InMemoryAnswerCache:
    """A bounded, thread-safe LRU cache of serialized Action Packs."""

    def __init__(self, *, maxsize: int = 256) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self._maxsize = maxsize
        self._store: OrderedDict[CacheKey, dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: CacheKey) -> dict[str, Any] | None:
        """Return the cached Action Pack for ``key`` (marking it most-recent)."""
        with self._lock:
            answer = self._store.get(key)
            if answer is not None:
                self._store.move_to_end(key)
            return answer

    def put(self, key: CacheKey, answer: dict[str, Any]) -> None:
        """Cache ``answer`` under ``key``, evicting the least-recent if over budget."""
        with self._lock:
            self._store[key] = answer
            self._store.move_to_end(key)
            while len(self._store) > self._maxsize:
                self._store.popitem(last=False)

    def invalidate_service(self, service_id: int) -> None:
        """Drop every cached answer for ``service_id`` (call on KB upsert, AD-12)."""
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
