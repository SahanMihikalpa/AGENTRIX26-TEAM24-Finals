"""Moderation use case — the human side of the B4 "serve-but-label" policy.

See [docs/agents/b4-moderation.md](../../../docs/agents/b4-moderation.md). Auto-
gathered / experience-sourced knowledge is served immediately (labelled "pending
verification") and queued here for a human to review:

* **promote** → ``verified``: the source is now trusted; A6 drops the "pending"
  label for everyone after.
* **reject** → ``rejected`` + **de-indexed**: the source is quarantined — its
  chunks are removed so it is no longer retrieved/served, while the ``source`` row
  is kept so dedup still blocks it from being re-ingested by a future gap loop.

An application **use case**: it owns the promote/reject *policy* (so the API route
stays a thin translator) and depends only on the :class:`KnowledgeStore` port.
"""

from __future__ import annotations

from app.domain.entities import Source, VerificationStatus
from app.domain.ports.cache import AnswerCache
from app.domain.ports.knowledge import KnowledgeStore


class ModerationService:
    """List the review queue and apply moderator promote/reject decisions."""

    def __init__(self, store: KnowledgeStore, cache: AnswerCache | None = None) -> None:
        self._store = store
        self._cache = cache

    def queue(self, *, limit: int = 50) -> list[Source]:
        """Sources still awaiting review (``auto_gathered`` / ``pending``)."""
        return self._store.list_sources_for_moderation(limit=limit)

    def promote(self, source_id: int) -> bool:
        """Mark a source ``verified``. ``False`` if the source id is unknown."""
        updated = self._store.set_source_verification_status(
            source_id, VerificationStatus.VERIFIED
        )
        if updated is None:
            return False
        # The served label for this service changes (pending → verified), so any
        # cached answers must be dropped (AD-12).
        self._invalidate_cache(self._store.get_service_ids_for_source(source_id))
        return True

    def reject(self, source_id: int) -> bool:
        """Quarantine a source: mark ``rejected`` and de-index its chunks.

        ``False`` if the source id is unknown (nothing changed).
        """
        updated = self._store.set_source_verification_status(
            source_id, VerificationStatus.REJECTED
        )
        if updated is None:
            return False
        # Capture the affected services *before* de-indexing removes the chunks.
        service_ids = self._store.get_service_ids_for_source(source_id)
        self._store.delete_chunks_for_source(source_id)
        self._invalidate_cache(service_ids)
        return True

    def _invalidate_cache(self, service_ids: list[int]) -> None:
        if self._cache is None:
            return
        for service_id in service_ids:
            self._cache.invalidate_service(service_id)
