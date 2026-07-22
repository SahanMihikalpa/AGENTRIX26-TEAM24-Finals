"""B3 · KB-Updater — persist curated records so the KB becomes self-expanding.

See [docs/agents/b3-kb-updater.md](../../../docs/agents/b3-kb-updater.md).
This is the step that actually grows the knowledge base (and caches the first
user's research for everyone after). For each curated record from B2 it:

1. **Dedups** by url + content hash (idempotent — re-running a gap loop is safe).
2. Writes the ``SOURCE`` (``auto_gathered``) and the structured rows
   (service / variant / requirements / fees / offices / district variation),
   attaching the ``source_id`` to every fact.
3. Chunks the raw text, **embeds it locally** (AD-4, same model as A4), and upserts
   the vectors with ``service_id`` metadata so A4 can retrieve it next loop.

It sets ``kb_updated`` so the supervisor re-runs A4. Services/variants are reused
when they already exist (slug / condition label), never overwriting ``verified``
data with ``auto_gathered`` data.
"""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.application.graph.state import GraphState
from app.domain.entities import (
    DistrictVariation,
    Fee,
    KBChunk,
    Office,
    OfficeType,
    Requirement,
    Service,
    ServiceVariant,
    Source,
    SourceType,
    VerificationStatus,
)
from app.domain.ports.embeddings import EmbeddingProvider
from app.domain.ports.knowledge import KnowledgeStore

_MAX_CHUNK_CHARS = 500


class KBUpdaterAgent:
    """Embed + upsert curated records into SQLite + Chroma (the writer)."""

    def __init__(
        self,
        store: KnowledgeStore,
        embedder: EmbeddingProvider,
        *,
        max_chunk_chars: int = _MAX_CHUNK_CHARS,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._max_chunk_chars = max_chunk_chars

    def __call__(self, state: GraphState) -> dict[str, Any]:
        written_service_id: int | None = None
        for record in state["curated"]:
            service_id = self._write_record(record)
            if service_id is not None:
                written_service_id = service_id

        result: dict[str, Any] = {"kb_updated": written_service_id is not None}
        # Hand the freshly-acquired service back to the answering path so the gap
        # loop converges — A4 re-retrieves with a real service_id instead of
        # looping on `service_unknown`. Only adopt it when we were filling an
        # unknown-service gap; a known-service gap keeps its existing service_id.
        if written_service_id is not None and state["service_unknown"]:
            result["service_id"] = written_service_id
            result["service_unknown"] = False
        return result

    # ── per-record write ─────────────────────────────────────────
    def _write_record(self, record: dict[str, Any]) -> int | None:
        """Write one curated record; return the service_id written, or ``None`` if deduped."""
        text = str(record["text"])
        src = record["source"]
        content_hash = _content_hash(text)
        if self._store.source_exists(url=src.get("url"), content_hash=content_hash):
            return None  # dedup — already ingested

        source_id = _require_id(
            self._store.upsert_source(
                self._build_source(src), content_hash=content_hash
            ).id
        )

        extraction = record["extraction"]
        service_id = self._resolve_service(extraction)
        variant_id = self._resolve_variant(service_id, extraction)
        self._write_requirements(variant_id, source_id, extraction)
        self._write_fees(variant_id, source_id, extraction)
        self._write_offices(service_id, extraction)
        self._write_district_variation(service_id, source_id, extraction)
        self._write_chunks(source_id, service_id, text)
        return service_id

    # ── catalog resolution (reuse-or-create) ─────────────────────
    def _resolve_service(self, extraction: dict[str, Any]) -> int:
        slug = str(extraction["service_slug"])
        for candidate in self._store.find_services(slug):
            if candidate.slug == slug:
                return _require_id(candidate.id)
        service = self._store.add_service(
            Service(
                name_en=str(extraction["service_name"]),
                slug=slug,
                category=str(extraction.get("category", "")),
                description=str(extraction.get("description", "")),
            )
        )
        return _require_id(service.id)

    def _resolve_variant(self, service_id: int, extraction: dict[str, Any]) -> int:
        label = str(extraction.get("condition_label") or "standard")
        for variant in self._store.list_variants(service_id):
            if variant.condition_label == label:
                return _require_id(variant.id)
        variant = self._store.add_variant(
            ServiceVariant(service_id=service_id, condition_label=label, description="")
        )
        return _require_id(variant.id)

    # ── structured rows ──────────────────────────────────────────
    def _write_requirements(
        self, variant_id: int, source_id: int, extraction: dict[str, Any]
    ) -> None:
        for req in extraction.get("requirements", []):
            self._store.add_requirement(
                Requirement(
                    variant_id=variant_id,
                    source_id=source_id,
                    document_name=str(req["document_name"]),
                    is_mandatory=bool(req.get("is_mandatory", True)),
                    notes=str(req.get("notes", "")),
                )
            )

    def _write_fees(self, variant_id: int, source_id: int, extraction: dict[str, Any]) -> None:
        for fee in extraction.get("fees", []):
            self._store.add_fee(
                Fee(
                    variant_id=variant_id,
                    source_id=source_id,
                    label=str(fee["label"]),
                    amount_lkr=_to_decimal(fee.get("amount_lkr", "0")),
                    notes=str(fee.get("notes", "")),
                )
            )

    def _write_offices(self, service_id: int, extraction: dict[str, Any]) -> None:
        default_district = str(extraction.get("district", ""))
        for office in extraction.get("offices", []):
            stored = self._store.add_office(
                Office(
                    name=str(office["name"]),
                    office_type=OfficeType.OTHER,
                    district=str(office.get("district") or default_district),
                    address=str(office.get("address", "")),
                    hours=str(office.get("hours", "")),
                    contact=str(office.get("contact", "")),
                )
            )
            self._store.link_service_office(service_id, _require_id(stored.id))

    def _write_district_variation(
        self, service_id: int, source_id: int, extraction: dict[str, Any]
    ) -> None:
        district = str(extraction.get("district", "")).strip()
        notes = str(extraction.get("district_notes", "")).strip()
        if district and notes:
            self._store.add_district_variation(
                DistrictVariation(
                    service_id=service_id,
                    source_id=source_id,
                    district=district,
                    notes=notes,
                )
            )

    # ── vectors ──────────────────────────────────────────────────
    def _write_chunks(self, source_id: int, service_id: int, text: str) -> None:
        pieces = _chunk_text(text, self._max_chunk_chars)
        if not pieces:
            return
        chunks = [
            KBChunk(source_id=source_id, service_id=service_id, content=piece, chunk_index=index)
            for index, piece in enumerate(pieces)
        ]
        self._store.upsert_chunks(chunks, self._embedder.embed_documents(pieces))

    @staticmethod
    def _build_source(src: dict[str, Any]) -> Source:
        return Source(
            title=str(src["title"]),
            url=src.get("url"),
            source_type=SourceType(src["source_type"]),
            published_date=_parse_date(src.get("published_date")),
            retrieved_date=_parse_date(src.get("retrieved_date")) or date.today(),
            confidence=float(src.get("confidence", 0.5)),
            verification_status=VerificationStatus(
                src.get("verification_status", "auto_gathered")
            ),
        )


# ── module helpers ───────────────────────────────────────────────
def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _chunk_text(text: str, max_chars: int) -> list[str]:
    """Greedy word-boundary chunking — small and deterministic for the MVP."""
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for word in words:
        if current and length + len(word) + 1 > max_chars:
            chunks.append(" ".join(current))
            current, length = [], 0
        current.append(word)
        length += len(word) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _parse_date(value: Any) -> date | None:
    return date.fromisoformat(str(value)) if value else None


def _require_id(value: int | None) -> int:
    if value is None:
        raise RuntimeError("knowledge store did not assign an id on insert")
    return value
