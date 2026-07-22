"""Smoke test for the Stage 0 delivery skeleton."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import create_app


def test_health_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "govguide-backend"
