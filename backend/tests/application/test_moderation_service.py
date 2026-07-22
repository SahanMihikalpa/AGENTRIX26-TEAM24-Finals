"""``ModerationService`` — queue + the promote/reject policy.

Uses bare (unseeded) stores so the queue and vector-search assertions are
unambiguous: the only sources/chunks present are the ones each test adds.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app.adapters.knowledge.chroma_sqlite import ChromaSqliteStore
from app.application.moderation import ModerationService
from app.domain.entities import (
    KBChunk,
    Service,
    Source,
    SourceType,
    VerificationStatus,
)
from app.infrastructure.cache import InMemoryAnswerCache
from tests.application.conftest import DeterministicEmbedder


def _store(tmp_path: Path) -> ChromaSqliteStore:
    return ChromaSqliteStore(
        sqlite_path=tmp_path / "kb.sqlite3", chroma_dir=tmp_path / "chroma"
    )


def _auto_source(store: ChromaSqliteStore, *, content_hash: str) -> Source:
    return store.upsert_source(
        Source(
            title="Business Reg",
            url=f"https://reg.gov.lk/{content_hash}",
            source_type=SourceType.PORTAL,
            retrieved_date=date(2026, 6, 20),
            confidence=0.5,
            verification_status=VerificationStatus.AUTO_GATHERED,
        ),
        content_hash=content_hash,
    )


def test_queue_lists_and_promote_verifies(tmp_path: Path) -> None:
    store = _store(tmp_path)
    service = ModerationService(store)
    source = _auto_source(store, content_hash="a")
    assert source.id is not None

    assert [s.id for s in service.queue()] == [source.id]
    assert service.promote(source.id) is True
    assert service.queue() == []  # promoted → no longer pending
    assert service.promote(99999) is False  # unknown id


def test_reject_quarantines_and_deindexes(
    tmp_path: Path, embedder: DeterministicEmbedder
) -> None:
    store = _store(tmp_path)
    service = ModerationService(store)
    source = _auto_source(store, content_hash="b")
    catalog = store.add_service(
        Service(name_en="Biz Reg", slug="biz_reg", category="c", description="d")
    )
    assert source.id is not None and catalog.id is not None
    store.upsert_chunks(
        [
            KBChunk(
                source_id=source.id,
                service_id=catalog.id,
                content="business name registration nic copy",
                chunk_index=0,
            )
        ],
        embedder.embed_documents(["business name registration nic copy"]),
    )
    assert store.search(embedder.embed_query("business registration"), top_k=5)

    assert service.reject(source.id) is True
    assert service.queue() == []  # rejected → dropped from the queue
    # de-indexed (no longer retrievable/served) ...
    assert store.search(embedder.embed_query("business registration"), top_k=5) == []
    # ... but the source row is kept so dedup still blocks re-ingestion
    assert store.source_exists(url=source.url, content_hash="b")
    assert service.reject(88888) is False


def _source_with_chunk(
    store: ChromaSqliteStore, embedder: DeterministicEmbedder, *, content_hash: str
) -> int:
    """Add an auto_gathered source with one chunk for a service; return the service id."""
    source = _auto_source(store, content_hash=content_hash)
    catalog = store.add_service(
        Service(name_en="Biz", slug=f"biz_{content_hash}", category="c", description="d")
    )
    assert source.id is not None and catalog.id is not None
    store.upsert_chunks(
        [KBChunk(source_id=source.id, service_id=catalog.id, content="biz", chunk_index=0)],
        embedder.embed_documents(["biz"]),
    )
    return catalog.id


def test_promote_invalidates_cached_answers(
    tmp_path: Path, embedder: DeterministicEmbedder
) -> None:
    store = _store(tmp_path)
    cache = InMemoryAnswerCache()
    service = ModerationService(store, cache)
    service_id = _source_with_chunk(store, embedder, content_hash="p")
    source_id = store.list_sources_for_moderation()[0].id
    assert source_id is not None
    cache.put_answer(service_id, {"service_label": "Biz"})

    assert service.promote(source_id) is True
    # promoting changes the served label (pending → verified) → cache dropped
    assert cache.get_answer(service_id) is None


def test_reject_invalidates_cached_answers(
    tmp_path: Path, embedder: DeterministicEmbedder
) -> None:
    store = _store(tmp_path)
    cache = InMemoryAnswerCache()
    service = ModerationService(store, cache)
    service_id = _source_with_chunk(store, embedder, content_hash="r")
    source_id = store.list_sources_for_moderation()[0].id
    assert source_id is not None
    cache.put_answer(service_id, {"service_label": "Biz"})

    assert service.reject(source_id) is True
    assert cache.get_answer(service_id) is None
