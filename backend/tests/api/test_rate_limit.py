"""Inbound HTTP rate limiting — the guard on the free-tier quota."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.rate_limit import SlidingWindowLimiter, build_rate_limit_middleware


class FakeClock:
    """A hand-cranked monotonic clock so the window is tested without sleeping."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# ── the limiter itself ────────────────────────────────────────────
def test_allows_up_to_the_limit_then_rejects() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(3, time_source=clock)

    assert [limiter.check("a") for _ in range(3)] == [None, None, None]
    retry_after = limiter.check("a")

    assert retry_after is not None
    assert retry_after == pytest.approx(60.0)


def test_window_slides_so_the_oldest_hit_frees_a_slot() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(2, time_source=clock)

    limiter.check("a")
    clock.advance(30)
    limiter.check("a")
    assert limiter.check("a") is not None  # both hits still inside the window

    clock.advance(31)  # the first hit is now 61s old → expired
    assert limiter.check("a") is None


def test_keys_are_independent() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(1, time_source=clock)

    assert limiter.check("a") is None
    assert limiter.check("b") is None  # b is not affected by a's spent budget
    assert limiter.check("a") is not None


def test_idle_keys_are_reaped_so_the_map_does_not_grow_forever() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(5, time_source=clock)

    for i in range(1100):
        limiter.check(f"client-{i}")
    clock.advance(120)  # every recorded hit is now outside the window
    limiter.check("fresh")

    assert len(limiter._hits) < 1100  # swept on the next touch


def test_rejects_a_non_positive_limit() -> None:
    with pytest.raises(ValueError):
        SlidingWindowLimiter(0)


# ── the middleware, wired into an app ─────────────────────────────
def _app(*, chat_rpm: int = 2, api_rpm: int = 3) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(build_rate_limit_middleware(chat_rpm=chat_rpm, api_rpm=api_rpm))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/chat")
    async def chat() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/moderation/queue")
    async def queue() -> list[str]:
        return []

    return app


def test_chat_is_capped_and_answers_429_with_retry_after() -> None:
    client = TestClient(_app(chat_rpm=2))

    assert client.post("/api/chat").status_code == 200
    assert client.post("/api/chat").status_code == 200

    blocked = client.post("/api/chat")
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) >= 1
    assert "quota" in blocked.json()["detail"]


def test_chat_and_other_api_routes_have_separate_budgets() -> None:
    client = TestClient(_app(chat_rpm=1, api_rpm=3))

    client.post("/api/chat")
    assert client.post("/api/chat").status_code == 429  # chat budget spent
    assert client.get("/api/moderation/queue").status_code == 200  # its own budget


def test_health_is_never_limited() -> None:
    client = TestClient(_app(chat_rpm=1, api_rpm=1))

    for _ in range(10):
        assert client.get("/health").status_code == 200


def test_clients_are_metered_separately_via_forwarded_for() -> None:
    client = TestClient(_app(chat_rpm=1))

    assert client.post("/api/chat", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert client.post("/api/chat", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 429
    assert client.post("/api/chat", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 200


def test_cors_wraps_the_rate_limiter() -> None:
    """Middleware order regression (main.create_app).

    Starlette makes the *last* registered middleware outermost, and
    ``user_middleware[0]`` is that outermost entry. CORS must sit outside the
    limiter: otherwise a 429 short-circuits before CORSMiddleware can add its
    headers, and the browser reports an opaque network failure instead of showing
    the "too many requests" message.
    """
    from app.api.main import create_app

    names = [entry.cls.__name__ for entry in create_app().user_middleware]

    assert "CORSMiddleware" in names, names
    assert "BaseHTTPMiddleware" in names, names  # the rate limiter
    assert names.index("CORSMiddleware") < names.index("BaseHTTPMiddleware"), names
