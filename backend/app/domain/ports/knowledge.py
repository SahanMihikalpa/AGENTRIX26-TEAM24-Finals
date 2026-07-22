"""Knowledge-base ports — the Repository sockets over SQLite + ChromaDB.

Two interfaces, both implemented by ``adapters/knowledge/chroma_sqlite.py``:

* :class:`KnowledgeStore` — structured catalog reads/writes (A2/A4, seeding, B3)
  and provenance-aware source/chunk writes with dedup.
* :class:`Retriever` — semantic vector search (A4).

Splitting reads-by-key from semantic search keeps each agent's dependency narrow.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

from app.domain.entities import (
    DistrictVariation,
    ExperienceReport,
    Fee,
    KBChunk,
    Office,
    Requirement,
    RetrievedChunk,
    Service,
    ServiceVariant,
    Source,
    VerificationStatus,
)


@runtime_checkable
class KnowledgeStore(Protocol):
    """Structured catalog + provenance store (the source of truth)."""

    # ── catalog writes (seeding / B3) ────────────────────────────
    def add_service(self, service: Service) -> Service: ...
    def add_variant(self, variant: ServiceVariant) -> ServiceVariant: ...
    def add_requirement(self, requirement: Requirement) -> Requirement: ...
    def add_fee(self, fee: Fee) -> Fee: ...
    def add_office(self, office: Office) -> Office: ...
    def link_service_office(self, service_id: int, office_id: int) -> None: ...
    def add_district_variation(
        self, variation: DistrictVariation
    ) -> DistrictVariation: ...

    # ── provenance / chunk writes + dedup (B3) ───────────────────
    def source_exists(self, *, url: str | None, content_hash: str) -> bool:
        """Whether a source with this URL or content hash is already stored."""
        ...

    def upsert_source(self, source: Source, *, content_hash: str | None = None) -> Source:
        """Insert/update a source; return it with its assigned ``id``."""
        ...

    def upsert_chunks(
        self, chunks: Sequence[KBChunk], embeddings: Sequence[Sequence[float]]
    ) -> None:
        """Persist chunks (SQLite) and their vectors (Chroma), zipped by index."""
        ...

    # ── catalog reads (A2 / A4) ──────────────────────────────────
    def find_services(self, query: str, *, limit: int = 5) -> list[Service]:
        """Candidate services matching a name/alias query (A2)."""
        ...

    def get_service(self, service_id: int) -> Service | None: ...

    def list_variants(self, service_id: int) -> list[ServiceVariant]: ...

    def get_requirements(self, variant_id: int) -> list[Requirement]: ...

    def get_fees(self, variant_id: int) -> list[Fee]: ...

    def get_offices(
        self, service_id: int, *, district: str | None = None
    ) -> list[Office]: ...

    # ── feedback + moderation (Stage 6b) ─────────────────────────
    def add_experience_report(self, report: ExperienceReport) -> ExperienceReport:
        """Persist a citizen experience report; return it with its assigned ``id``."""
        ...

    def list_sources_for_moderation(self, *, limit: int = 50) -> list[Source]:
        """Sources still awaiting review (``auto_gathered`` / ``pending``), newest first."""
        ...

    def set_source_verification_status(
        self, source_id: int, status: VerificationStatus
    ) -> Source | None:
        """Set a source's verification status (moderator promote/reject).

        Returns the updated source, or ``None`` if no source has that id.
        """
        ...

    def delete_chunks_for_source(self, source_id: int) -> int:
        """Remove a source's chunks from SQLite + the vector index (reject quarantine).

        The ``source`` row is intentionally kept so dedup still blocks re-ingestion.
        Returns the number of chunks removed.
        """
        ...

    def get_service_ids_for_source(self, source_id: int) -> list[int]:
        """The distinct services a source's chunks belong to (for cache invalidation)."""
        ...


@runtime_checkable
class Retriever(Protocol):
    """Semantic search over embedded knowledge-base chunks."""

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        filters: Mapping[str, object] | None = None,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Return the top-k chunks for a query vector, with provenance + scores."""
        ...
