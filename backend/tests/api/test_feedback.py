"""``POST /api/experience-reports`` — persist + best-effort B2→B3, end-to-end."""

from __future__ import annotations

from app.application.agents.schemas import CuratedExtraction, CuratedRequirement
from tests.api.conftest import ClientFactory


def test_submit_report_persists_and_ingests(build_client: ClientFactory) -> None:
    client, _ = build_client(
        {
            CuratedExtraction: CuratedExtraction(
                service_name="Passport Renewal",
                service_slug="passport_renewal",  # seeded → B3 reuses it
                condition_label="standard",
                requirements=[CuratedRequirement(document_name="Old passport")],
                district="Colombo",
                extraction_confidence=0.9,
            )
        }
    )

    response = client.post(
        "/api/experience-reports",
        json={"outcome": "extra_doc", "text": "They also asked for the old passport."},
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["status"] == "pending"

    # the report grew the KB → its source surfaces in the moderation queue
    queue = client.get("/api/moderation/queue").json()
    assert any(item["source_type"] == "experience" for item in queue)


def test_invalid_outcome_is_rejected(build_client: ClientFactory) -> None:
    client, _ = build_client({})
    response = client.post(
        "/api/experience-reports", json={"outcome": "banana", "text": "x"}
    )
    assert response.status_code == 422  # not a valid ReportOutcome


def test_vague_report_recorded_without_ingestion(build_client: ClientFactory) -> None:
    # B2 finds no mappable service → dropped; only the feedback record remains.
    client, _ = build_client({CuratedExtraction: CuratedExtraction()})
    response = client.post(
        "/api/experience-reports", json={"outcome": "matched", "text": "All correct!"}
    )
    assert response.status_code == 201
    assert client.get("/api/moderation/queue").json() == []


def test_empty_text_report_skips_ingestion(build_client: ClientFactory) -> None:
    # No text → no B2 call (no LLM script needed); the report is still recorded.
    client, _ = build_client({})
    response = client.post(
        "/api/experience-reports", json={"outcome": "matched", "session_id": "unknown"}
    )
    assert response.status_code == 201
    assert client.get("/api/moderation/queue").json() == []
