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

    def __init__(self, store: KnowledgeStore, *, cache: AnswerCache | None = None) -> None:
        self._store = store
        self._cache = cache

    def _invalidate(self) -> None:
        """Clear every cached answer after a moderation decision.

        Promote/reject change a *source*, and a source can back facts for any
        number of services — mapping it back to the affected service ids would
        need a reverse index we don't keep. Moderation is a rare, human-paced
        action and the cache is small, so clearing wholesale is the cheap,
        obviously-correct choice over serving an answer with a stale trust label.
        """
        if self._cache is not None:
            self._cache.clear()

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
        # A6 renders the trust label from the source, so a cached pack would keep
        # saying "pending verification" after the moderator said otherwise.
        self._invalidate()
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
        self._store.delete_chunks_for_source(source_id)
        # Quarantining is the case that matters most: without this, a cached pack
        # would keep serving facts from a source a moderator just pulled.
        self._invalidate()
        return True
