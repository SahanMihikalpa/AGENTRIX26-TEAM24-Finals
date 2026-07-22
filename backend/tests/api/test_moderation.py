"""``GET /api/moderation/queue`` + promote/reject, driven through the API."""

from __future__ import annotations

from datetime import date

from app.adapters.knowledge.chroma_sqlite import ChromaSqliteStore
from app.domain.entities import Source, SourceType, VerificationStatus
from tests.api.conftest import ClientFactory


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


def test_queue_lists_auto_gathered_then_promote(build_client: ClientFactory) -> None:
    client, store = build_client({})
    source = _auto_source(store, content_hash="a")

    queue = client.get("/api/moderation/queue").json()
    assert [item["source_id"] for item in queue] == [source.id]
    assert queue[0]["verification_status"] == "auto_gathered"

    promote = client.post(f"/api/moderation/{source.id}/promote")
    assert promote.status_code == 200
    assert promote.json() == {"ok": True}
    assert client.get("/api/moderation/queue").json() == []  # promoted → gone

    assert client.post("/api/moderation/99999/promote").status_code == 404


def test_reject_drops_from_queue_but_keeps_source_row(
    build_client: ClientFactory,
) -> None:
    client, store = build_client({})
    source = _auto_source(store, content_hash="b")
    assert source.id is not None

    reject = client.post(f"/api/moderation/{source.id}/reject")
    assert reject.status_code == 200
    assert reject.json()["ok"] is True
    assert client.get("/api/moderation/queue").json() == []  # rejected → gone
    # the row is kept so dedup still blocks re-ingestion
    assert store.source_exists(url=source.url, content_hash="b")

    assert client.post("/api/moderation/88888/reject").status_code == 404
