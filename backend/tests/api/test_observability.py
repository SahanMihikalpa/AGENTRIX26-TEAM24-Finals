"""Correlation-id middleware (Stage 7a) — generated + propagated, end-to-end."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import create_app


def test_response_carries_a_generated_correlation_id() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    correlation_id = response.headers.get("x-correlation-id")
    assert correlation_id is not None and len(correlation_id) >= 8


def test_incoming_correlation_id_is_echoed_back() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            "/health", headers={"X-Correlation-ID": "trace-me-123"}
        )
    assert response.headers.get("x-correlation-id") == "trace-me-123"
