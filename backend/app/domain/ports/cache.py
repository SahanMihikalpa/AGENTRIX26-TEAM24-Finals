"""``AnswerCache`` port — short-circuit repeated Action-Pack generation (AD-12).

Identical ``service + variant + district`` questions produce identical Action
Packs, and generating one costs the scarce part of the budget: an A5 grading call
plus an A6 composition call. Caching that result is what lets a demo re-run, or
two citizens asking the same thing, cost nothing.

The cached value is the **serialized** Action Pack — the same JSON-ready ``dict``
that lives in ``GraphState["answer"]`` and that ``ActionPackDTO`` validates on the
way out. Keeping the cache in the state's own representation (rather than the
``ActionPack`` entity) means no inverse deserializer is needed, and it keeps the
door open to the durable SQLite tier docs/04 anticipates.

Correctness rests on **invalidation**: B3 drops a service's entries the moment it
upserts new knowledge for it, so a freshly-expanded KB can never serve a stale
answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


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


class AnswerCache(Protocol):
    """Stores generated Action Packs, keyed by what determines their content."""

    def get(self, key: CacheKey) -> dict[str, Any] | None:
        """Return the cached serialized Action Pack, or ``None`` on a miss."""
        ...

    def put(self, key: CacheKey, answer: dict[str, Any]) -> None:
        """Cache ``answer`` under ``key``."""
        ...

    def invalidate_service(self, service_id: int) -> None:
        """Drop every cached answer for ``service_id`` (called on KB upsert)."""
        ...

    def clear(self) -> None:
        """Drop everything (used when a change's blast radius is unknown)."""
        ...
