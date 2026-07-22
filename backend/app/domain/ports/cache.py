"""Query→answer cache port (AD-12).

The self-expanding loop is quota-scarce, so an identical request — same
``service`` + ``variant`` + ``district`` — should skip the whole graph and replay
the previously generated answer. This port is the socket the graph wiring uses; the
in-memory implementation lives in ``infrastructure/cache.py``.

The cached value is the **serialised** answer dict (exactly what A6 writes to the
``GraphState`` and what the API serves), keyed by primitive args — so the port
stays free of any transport- or infrastructure-specific types and the
``application`` layer can depend on it without importing ``infrastructure``.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AnswerCache(Protocol):
    """A query→answer cache keyed by service (optionally narrowed by variant/district)."""

    def get_answer(
        self,
        service_id: int,
        *,
        variant_id: int | None = None,
        district: str | None = None,
    ) -> dict[str, Any] | None:
        """Return the cached answer for this resolved request, or ``None`` on a miss."""
        ...

    def put_answer(
        self,
        service_id: int,
        answer: dict[str, Any],
        *,
        variant_id: int | None = None,
        district: str | None = None,
    ) -> None:
        """Cache ``answer`` under the resolved (service, variant, district) key."""
        ...

    def invalidate_service(self, service_id: int) -> None:
        """Drop every cached answer for a service (on KB upsert / moderation change)."""
        ...
