"""Integration tests for the SQLite + Chroma knowledge store."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from app.adapters.knowledge.chroma_sqlite import ChromaSqliteStore
from app.domain.entities import (
    ExperienceReport,
    Fee,
    KBChunk,
    Office,
    OfficeType,
    ReportOutcome,
    ReportStatus,
    Requirement,
    Service,
    ServiceVariant,
    Source,
    SourceType,
    VerificationStatus,
)


def _add_source(store: ChromaSqliteStore) -> Source:
    return store.upsert_source(
        Source(
            title="Gazette 2026",
            url="https://x.gov.lk/g1",
            source_type=SourceType.GAZETTE,
            retrieved_date=date(2026, 6, 20),
            confidence=1.0,
            verification_status=VerificationStatus.VERIFIED,
        ),
        content_hash="hash-1",
    )


def test_service_crud_and_find(store: ChromaSqliteStore) -> None:
    service = store.add_service(
        Service(
            name_en="NIC Renewal",
            slug="nic_renewal",
            category="identity",
            description="Renew your National Identity Card",
        )
    )
    assert service.id is not None
    fetched = store.get_service(service.id)
    assert fetched is not None
    assert fetched.slug == "nic_renewal"
    assert any(s.slug == "nic_renewal" for s in store.find_services("Identity Card"))


def test_find_services_keyword_overlap_matches_natural_language(store: ChromaSqliteStore) -> None:
    store.add_service(
        Service(
            name_en="Land Deed Transfer & Registration",
            slug="land-deed-transfer",
            category="Land & Property",
            description="Register a deed transferring ownership of land",
        )
    )
    store.add_service(
        Service(
            name_en="National Identity Card Issuance",
            slug="nic-issuance",
            category="Civil Registration & Identity",
            description="Obtain a NIC",
        )
    )
    # A natural-language question that is not a literal substring of any field:
    # the old whole-query LIKE returned nothing here and forced the gap path.
    matches = store.find_services("Transfer my late father's land to my name")
    assert matches
    assert matches[0].slug == "land-deed-transfer"
    # A genuinely unknown service still yields nothing → caller routes to the gap path.
    assert store.find_services("renew my passport urgently") == []


def test_find_services_rejects_generic_word_false_positives(store: ChromaSqliteStore) -> None:
    store.add_service(
        Service(
            name_en="Land Deed Transfer & Registration",
            slug="land-deed-transfer",
            category="Land & Property",
            description="Registering a deed that transfers ownership of land",
        )
    )
    store.add_service(
        Service(
            name_en="National Identity Card Issuance",
            slug="nic-issuance",
            category="Civil Registration & Identity",
            description="Obtain a NIC",
        )
    )
    # A UGC/university request shares only the generic word "register"/"registration"
    # with the Land Deed name — it must NOT match (→ the caller routes to the gap path),
    # not return a land deed.
    assert store.find_services("register with UGC to apply to university") == []
    # but the discriminative nouns still resolve the right service
    assert store.find_services("register my land deed")[0].slug == "land-deed-transfer"


def test_variant_requirement_fee_roundtrip(store: ChromaSqliteStore) -> None:
    source = _add_source(store)
    service = store.add_service(
        Service(
            name_en="Land Deed Transfer",
            slug="land_deed_transfer",
            category="land",
            description="d",
        )
    )
    assert service.id is not None
    variant = store.add_variant(
        ServiceVariant(service_id=service.id, condition_label="inheritance", description="d")
    )
    assert variant.id is not None
    assert source.id is not None
    store.add_requirement(
        Requirement(
            variant_id=variant.id,
            source_id=source.id,
            document_name="Original deed",
            is_mandatory=True,
        )
    )
    store.add_fee(
        Fee(
            variant_id=variant.id,
            source_id=source.id,
            label="Stamp duty",
            amount_lkr=Decimal("1500.00"),
        )
    )

    assert [v.condition_label for v in store.list_variants(service.id)] == ["inheritance"]
    requirements = store.get_requirements(variant.id)
    assert requirements[0].document_name == "Original deed"
    assert requirements[0].is_mandatory is True
    fees = store.get_fees(variant.id)
    assert fees[0].amount_lkr == Decimal("1500.00")


def test_offices_filtered_by_district(store: ChromaSqliteStore) -> None:
    service = store.add_service(Service(name_en="X", slug="x", category="c", description="d"))
    assert service.id is not None
    office = store.add_office(
        Office(
            name="DS Galle",
            office_type=OfficeType.DS,
            district="Galle",
            address="Main St",
            hours="9-4",
            contact="011",
        )
    )
    assert office.id is not None
    store.link_service_office(service.id, office.id)

    assert [o.name for o in store.get_offices(service.id)] == ["DS Galle"]
    assert store.get_offices(service.id, district="Galle")
    assert store.get_offices(service.id, district="Kandy") == []


def test_source_dedup(store: ChromaSqliteStore) -> None:
    _add_source(store)
    assert store.source_exists(url="https://x.gov.lk/g1", content_hash="different")
    assert store.source_exists(url=None, content_hash="hash-1")
    assert not store.source_exists(url="https://y.gov.lk", content_hash="nope")


def test_chunk_upsert_and_semantic_search(store: ChromaSqliteStore, embedder) -> None:
    source = _add_source(store)
    service = store.add_service(
        Service(name_en="Passport", slug="passport", category="travel", description="d")
    )
    assert source.id is not None
    assert service.id is not None
    chunks = [
        KBChunk(
            source_id=source.id,
            service_id=service.id,
            content="passport application requires birth certificate",
            chunk_index=0,
        ),
        KBChunk(
            source_id=source.id,
            service_id=service.id,
            content="driving licence renewal fee schedule",
            chunk_index=1,
        ),
    ]
    store.upsert_chunks(chunks, embedder.embed_documents([c.content for c in chunks]))

    results = store.search(embedder.embed_query("passport birth certificate"), top_k=2)
    assert results
    assert results[0].content.startswith("passport")
    assert results[0].source.id == source.id

    filtered = store.search(
        embedder.embed_query("passport"), filters={"service_id": service.id}, top_k=5
    )
    assert filtered
    assert all(r.service_id == service.id for r in filtered)


# ── feedback + moderation (Stage 6b) ─────────────────────────────
def _add_source_with_status(
    store: ChromaSqliteStore, status: VerificationStatus, *, title: str, content_hash: str
) -> Source:
    return store.upsert_source(
        Source(
            title=title,
            url=f"https://x.gov.lk/{content_hash}",
            source_type=SourceType.PORTAL,
            retrieved_date=date(2026, 6, 20),
            confidence=0.5,
            verification_status=status,
        ),
        content_hash=content_hash,
    )


def test_add_experience_report_persists(store: ChromaSqliteStore) -> None:
    report = ExperienceReport(
        service_id=None,  # nullable FK: a report may have no resolved service
        district="Colombo",
        report_text="They also asked for a utility bill.",
        reported_outcome=ReportOutcome.EXTRA_DOC,
        status=ReportStatus.PENDING,
        created_at=datetime(2026, 6, 21, 9, 0, tzinfo=UTC),
    )
    first = store.add_experience_report(report)
    second = store.add_experience_report(report)
    assert first.id is not None and second.id is not None
    assert second.id != first.id  # real INSERTs, not an echo
    assert first.reported_outcome is ReportOutcome.EXTRA_DOC


def test_list_sources_for_moderation_filters_and_orders(store: ChromaSqliteStore) -> None:
    _add_source_with_status(store, VerificationStatus.VERIFIED, title="V", content_hash="v")
    auto = _add_source_with_status(
        store, VerificationStatus.AUTO_GATHERED, title="A", content_hash="a"
    )
    pending = _add_source_with_status(
        store, VerificationStatus.PENDING, title="P", content_hash="p"
    )
    _add_source_with_status(store, VerificationStatus.REJECTED, title="R", content_hash="r")

    queue = store.list_sources_for_moderation()
    # only auto_gathered + pending, newest (highest id) first
    assert [s.id for s in queue] == [pending.id, auto.id]


def test_set_source_verification_status(store: ChromaSqliteStore) -> None:
    source = _add_source_with_status(
        store, VerificationStatus.AUTO_GATHERED, title="A", content_hash="a"
    )
    assert source.id is not None

    promoted = store.set_source_verification_status(source.id, VerificationStatus.VERIFIED)
    assert promoted is not None
    assert promoted.verification_status is VerificationStatus.VERIFIED
    # persisted: it drops out of the moderation queue
    assert store.list_sources_for_moderation() == []
    # unknown id → None
    assert store.set_source_verification_status(9999, VerificationStatus.VERIFIED) is None


def test_delete_chunks_for_source_quarantines(
    store: ChromaSqliteStore, embedder
) -> None:
    source = _add_source_with_status(
        store, VerificationStatus.AUTO_GATHERED, title="A", content_hash="a"
    )
    service = store.add_service(Service(name_en="X", slug="x", category="c", description="d"))
    assert source.id is not None and service.id is not None
    chunks = [
        KBChunk(
            source_id=source.id,
            service_id=service.id,
            content="business name registration nic copy",
            chunk_index=0,
        )
    ]
    store.upsert_chunks(chunks, embedder.embed_documents([c.content for c in chunks]))
    assert store.search(embedder.embed_query("business registration"), top_k=5)

    removed = store.delete_chunks_for_source(source.id)
    assert removed == 1
    # de-indexed (not served) ...
    assert store.search(embedder.embed_query("business registration"), top_k=5) == []
    # ... but the source row is kept so dedup still blocks re-ingestion
    assert store.source_exists(url=source.url, content_hash="a")
