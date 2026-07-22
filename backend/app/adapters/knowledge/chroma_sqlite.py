"""SQLite + ChromaDB implementation of the knowledge ports (Repository).

* SQLite (stdlib ``sqlite3``) is the source of truth for structured facts and
  provenance — schema in ``schema.sql``.
* ChromaDB holds chunk vectors for semantic retrieval; we supply bge vectors
  explicitly, so Chroma's built-in embedding function is unused.

Money is stored as TEXT to preserve :class:`~decimal.Decimal` precision; dates as
ISO strings; enums by value.
"""

from __future__ import annotations

import re
import sqlite3
import threading
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.domain.entities import (
    DistrictVariation,
    ExperienceReport,
    Fee,
    KBChunk,
    Office,
    OfficeType,
    Requirement,
    RetrievedChunk,
    Service,
    ServiceVariant,
    Source,
    SourceType,
    VerificationStatus,
)

_COLLECTION = "kb_chunks"
_NO_SERVICE = -1  # Chroma metadata can't hold None; sentinel for "chunk has no service"


class ChromaSqliteStore:
    """Concrete :class:`KnowledgeStore` + :class:`Retriever` over SQLite + Chroma."""

    def __init__(self, sqlite_path: Path, chroma_dir: Path) -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(sqlite_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()
        self._client: Any = chromadb.PersistentClient(
            path=str(chroma_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection: Any = self._client.get_or_create_collection(
            name=_COLLECTION, metadata={"hnsw:space": "cosine"}
        )

    def _init_schema(self) -> None:
        ddl = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
        with self._lock:
            self._conn.executescript(ddl)
            self._conn.commit()

    # ── catalog writes ───────────────────────────────────────────
    def add_service(self, service: Service) -> Service:
        new_id = self._insert(
            "INSERT INTO service (slug, name_en, category, description) VALUES (?,?,?,?)",
            (service.slug, service.name_en, service.category, service.description),
        )
        return replace(service, id=new_id)

    def add_variant(self, variant: ServiceVariant) -> ServiceVariant:
        new_id = self._insert(
            "INSERT INTO service_variant (service_id, condition_label, description)"
            " VALUES (?,?,?)",
            (variant.service_id, variant.condition_label, variant.description),
        )
        return replace(variant, id=new_id)

    def add_requirement(self, requirement: Requirement) -> Requirement:
        new_id = self._insert(
            "INSERT INTO requirement (variant_id, source_id, document_name, is_mandatory, notes)"
            " VALUES (?,?,?,?,?)",
            (
                requirement.variant_id,
                requirement.source_id,
                requirement.document_name,
                int(requirement.is_mandatory),
                requirement.notes,
            ),
        )
        return replace(requirement, id=new_id)

    def add_fee(self, fee: Fee) -> Fee:
        new_id = self._insert(
            "INSERT INTO fee (variant_id, source_id, label, amount_lkr, notes) VALUES (?,?,?,?,?)",
            (fee.variant_id, fee.source_id, fee.label, str(fee.amount_lkr), fee.notes),
        )
        return replace(fee, id=new_id)

    def add_office(self, office: Office) -> Office:
        new_id = self._insert(
            "INSERT INTO office"
            " (name, office_type, district, address, hours, contact, geo_lat, geo_lng)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (
                office.name,
                office.office_type.value,
                office.district,
                office.address,
                office.hours,
                office.contact,
                office.geo_lat,
                office.geo_lng,
            ),
        )
        return replace(office, id=new_id)

    def link_service_office(self, service_id: int, office_id: int) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO service_office (service_id, office_id) VALUES (?,?)",
                (service_id, office_id),
            )
            self._conn.commit()

    def add_district_variation(self, variation: DistrictVariation) -> DistrictVariation:
        new_id = self._insert(
            "INSERT INTO district_variation (service_id, source_id, district, notes)"
            " VALUES (?,?,?,?)",
            (variation.service_id, variation.source_id, variation.district, variation.notes),
        )
        return replace(variation, id=new_id)

    # ── provenance / chunk writes + dedup ────────────────────────
    def source_exists(self, *, url: str | None, content_hash: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM source WHERE (url IS NOT NULL AND url = ?) OR content_hash = ? LIMIT 1",
            (url, content_hash),
        )
        return cur.fetchone() is not None

    def upsert_source(self, source: Source, *, content_hash: str | None = None) -> Source:
        new_id = self._insert(
            "INSERT INTO source"
            " (title, url, source_type, published_date, retrieved_date, confidence,"
            " verification_status, content_hash)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (
                source.title,
                source.url,
                source.source_type.value,
                _date_to_str(source.published_date),
                _date_to_str(source.retrieved_date),
                source.confidence,
                source.verification_status.value,
                content_hash,
            ),
        )
        return replace(source, id=new_id)

    def upsert_chunks(
        self, chunks: Sequence[KBChunk], embeddings: Sequence[Sequence[float]]
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must be the same length")
        if not chunks:
            return
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[Mapping[str, object]] = []
        vectors: list[list[float]] = []
        with self._lock:
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                cur = self._conn.execute(
                    "INSERT INTO kb_chunk (source_id, service_id, content, vector_ref, chunk_index)"
                    " VALUES (?,?,?,?,?)",
                    (chunk.source_id, chunk.service_id, chunk.content, None, chunk.chunk_index),
                )
                vector_ref = f"chunk-{cur.lastrowid}"
                self._conn.execute(
                    "UPDATE kb_chunk SET vector_ref = ? WHERE id = ?", (vector_ref, cur.lastrowid)
                )
                ids.append(vector_ref)
                documents.append(chunk.content)
                metadatas.append(
                    {
                        "source_id": chunk.source_id,
                        "service_id": _NO_SERVICE if chunk.service_id is None else chunk.service_id,
                        "chunk_index": chunk.chunk_index,
                    }
                )
                vectors.append(list(embedding))
            self._conn.commit()
        self._collection.upsert(
            ids=ids, embeddings=vectors, documents=documents, metadatas=metadatas
        )

    # ── catalog reads ────────────────────────────────────────────
    def find_services(self, query: str, *, limit: int = 5) -> list[Service]:
        """Keyword-overlap service search (lexical, ranked).

        The catalog is small, so we score every service by how many query keywords
        appear in its name/slug/description and return the best matches. This is far
        more robust to natural-language phrasing than the old whole-query ``LIKE``,
        which only matched when the *entire* question was a literal substring of a
        field — so questions like "transfer my late father's land to my name" found
        nothing and were wrongly sent down the gap path. With no usable keywords we
        return the catalog head so callers still get candidates.
        """
        services = [_row_to_service(row) for row in self._conn.execute("SELECT * FROM service")]
        keywords = _keywords(query)
        if not keywords:
            return services[:limit]
        scored: list[tuple[int, Service]] = []
        for service in services:
            haystack = f"{service.name_en} {service.slug} {service.description}".lower()
            score = sum(1 for keyword in keywords if keyword in haystack)
            if score:
                scored.append((score, service))
        scored.sort(key=lambda item: item[0], reverse=True)  # most keyword hits first (stable)
        return [service for _, service in scored[:limit]]

    def get_service(self, service_id: int) -> Service | None:
        row = self._conn.execute("SELECT * FROM service WHERE id = ?", (service_id,)).fetchone()
        return _row_to_service(row) if row is not None else None

    def list_variants(self, service_id: int) -> list[ServiceVariant]:
        rows = self._conn.execute(
            "SELECT * FROM service_variant WHERE service_id = ?", (service_id,)
        ).fetchall()
        return [_row_to_variant(row) for row in rows]

    def get_requirements(self, variant_id: int) -> list[Requirement]:
        rows = self._conn.execute(
            "SELECT * FROM requirement WHERE variant_id = ?", (variant_id,)
        ).fetchall()
        return [_row_to_requirement(row) for row in rows]

    def get_fees(self, variant_id: int) -> list[Fee]:
        rows = self._conn.execute(
            "SELECT * FROM fee WHERE variant_id = ?", (variant_id,)
        ).fetchall()
        return [_row_to_fee(row) for row in rows]

    def get_offices(self, service_id: int, *, district: str | None = None) -> list[Office]:
        sql = (
            "SELECT o.* FROM office o JOIN service_office so ON so.office_id = o.id"
            " WHERE so.service_id = ?"
        )
        params: tuple[object, ...] = (service_id,)
        if district is not None:
            sql += " AND o.district = ?"
            params = (service_id, district)
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_office(row) for row in rows]

    # ── feedback + moderation ────────────────────────────────────
    def add_experience_report(self, report: ExperienceReport) -> ExperienceReport:
        new_id = self._insert(
            "INSERT INTO experience_report"
            " (service_id, district, report_text, reported_outcome, status, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (
                report.service_id,
                report.district,
                report.report_text,
                report.reported_outcome.value,
                report.status.value,
                report.created_at.isoformat(),
            ),
        )
        return replace(report, id=new_id)

    def list_sources_for_moderation(self, *, limit: int = 50) -> list[Source]:
        rows = self._conn.execute(
            "SELECT * FROM source WHERE verification_status IN (?, ?) ORDER BY id DESC LIMIT ?",
            (
                VerificationStatus.AUTO_GATHERED.value,
                VerificationStatus.PENDING.value,
                limit,
            ),
        ).fetchall()
        return [_row_to_source(row) for row in rows]

    def set_source_verification_status(
        self, source_id: int, status: VerificationStatus
    ) -> Source | None:
        with self._lock:
            self._conn.execute(
                "UPDATE source SET verification_status = ? WHERE id = ?",
                (status.value, source_id),
            )
            self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM source WHERE id = ?", (source_id,)
        ).fetchone()
        return _row_to_source(row) if row is not None else None

    def delete_chunks_for_source(self, source_id: int) -> int:
        with self._lock:
            rows = self._conn.execute(
                "SELECT vector_ref FROM kb_chunk WHERE source_id = ?", (source_id,)
            ).fetchall()
            self._conn.execute("DELETE FROM kb_chunk WHERE source_id = ?", (source_id,))
            self._conn.commit()
        vector_refs = [row["vector_ref"] for row in rows if row["vector_ref"]]
        if vector_refs:
            self._collection.delete(ids=vector_refs)
        return len(rows)

    def get_service_ids_for_source(self, source_id: int) -> list[int]:
        rows = self._conn.execute(
            "SELECT DISTINCT service_id FROM kb_chunk"
            " WHERE source_id = ? AND service_id IS NOT NULL",
            (source_id,),
        ).fetchall()
        return [int(row["service_id"]) for row in rows]

    # ── semantic search (Retriever) ──────────────────────────────
    def search(
        self,
        query_embedding: Sequence[float],
        *,
        filters: Mapping[str, object] | None = None,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        result = self._collection.query(
            query_embeddings=[list(query_embedding)],
            n_results=top_k,
            where=_build_where(filters),
        )
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        sources = self._get_sources({int(m["source_id"]) for m in metadatas})
        chunks: list[RetrievedChunk] = []
        for document, meta, distance in zip(documents, metadatas, distances, strict=True):
            service_id = int(meta["service_id"])
            chunks.append(
                RetrievedChunk(
                    content=str(document),
                    score=1.0 - float(distance),  # cosine distance → similarity
                    source=sources[int(meta["source_id"])],
                    service_id=None if service_id == _NO_SERVICE else service_id,
                    chunk_index=int(meta["chunk_index"]),
                )
            )
        return chunks

    # ── internals ────────────────────────────────────────────────
    def _insert(self, sql: str, params: tuple[object, ...]) -> int:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            row_id = cur.lastrowid
        if row_id is None:  # pragma: no cover - sqlite always sets lastrowid on INSERT
            raise RuntimeError("INSERT did not return a row id")
        return row_id

    def _get_sources(self, source_ids: set[int]) -> dict[int, Source]:
        if not source_ids:
            return {}
        placeholders = ",".join("?" for _ in source_ids)
        rows = self._conn.execute(
            f"SELECT * FROM source WHERE id IN ({placeholders})", tuple(source_ids)
        ).fetchall()
        return {int(row["id"]): _row_to_source(row) for row in rows}


_SERVICE_STOPWORDS = frozenset({
    "a", "an", "and", "are", "at", "do", "for", "from", "get", "how", "i", "in", "into",
    "is", "it", "me", "my", "need", "new", "obtain", "of", "on", "or", "please", "the",
    "to", "want", "with", "you", "your",
})


def _keywords(query: str) -> list[str]:
    """Distinct, meaningful lowercase tokens from a query (for service matching)."""
    keywords: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[a-z0-9]+", query.lower()):
        if len(token) >= 3 and token not in _SERVICE_STOPWORDS and token not in seen:
            seen.add(token)
            keywords.append(token)
    return keywords


def _build_where(filters: Mapping[str, object] | None) -> Mapping[str, object] | None:
    if not filters:
        return None
    clauses = [{key: value} for key, value in filters.items()]
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def _date_to_str(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


# ── row → entity mappers ─────────────────────────────────────────
def _row_to_service(row: sqlite3.Row) -> Service:
    return Service(
        id=int(row["id"]),
        slug=row["slug"],
        name_en=row["name_en"],
        category=row["category"],
        description=row["description"],
    )


def _row_to_variant(row: sqlite3.Row) -> ServiceVariant:
    return ServiceVariant(
        id=int(row["id"]),
        service_id=int(row["service_id"]),
        condition_label=row["condition_label"],
        description=row["description"],
    )


def _row_to_requirement(row: sqlite3.Row) -> Requirement:
    return Requirement(
        id=int(row["id"]),
        variant_id=int(row["variant_id"]),
        source_id=int(row["source_id"]),
        document_name=row["document_name"],
        is_mandatory=bool(row["is_mandatory"]),
        notes=row["notes"],
    )


def _row_to_fee(row: sqlite3.Row) -> Fee:
    return Fee(
        id=int(row["id"]),
        variant_id=int(row["variant_id"]),
        source_id=int(row["source_id"]),
        label=row["label"],
        amount_lkr=Decimal(row["amount_lkr"]),
        notes=row["notes"],
    )


def _row_to_office(row: sqlite3.Row) -> Office:
    return Office(
        id=int(row["id"]),
        name=row["name"],
        office_type=OfficeType(row["office_type"]),
        district=row["district"],
        address=row["address"],
        hours=row["hours"],
        contact=row["contact"],
        geo_lat=row["geo_lat"],
        geo_lng=row["geo_lng"],
    )


def _row_to_source(row: sqlite3.Row) -> Source:
    return Source(
        id=int(row["id"]),
        title=row["title"],
        url=row["url"],
        source_type=SourceType(row["source_type"]),
        published_date=date.fromisoformat(row["published_date"]) if row["published_date"] else None,
        retrieved_date=date.fromisoformat(row["retrieved_date"]),
        confidence=float(row["confidence"]),
        verification_status=VerificationStatus(row["verification_status"]),
    )
