"""Per-client HTTP rate limiting for the ``/api`` surface.

This is a **different** guard from :class:`~app.infrastructure.llm_gateway.LLMGateway`'s
token bucket. That one paces the backend's *outbound* Gemini/Groq calls so the
process stays under the free-tier ceiling — but it does so by *waiting*, which
means an unbounded flood of inbound ``POST /api/chat`` requests still consumes the
whole daily quota, just more slowly. This middleware is the *inbound* half: it
rejects excess callers outright with ``429`` before any agent work begins.

Design notes:

* **Sliding window, per client.** A deque of hit timestamps per key; anything
  older than the window is discarded on touch. More accurate than a fixed window
  (no double-rate burst across a boundary) and cheap at this scale.
* **In-memory.** Matches the single-process deployment (one uvicorn container). A
  multi-replica deployment would need a shared store — noted rather than
  pretended-away.
* **Chat is metered separately.** ``/api/chat`` is the only route that spends LLM
  quota, so it gets its own, tighter budget; the cheap read/write routes share a
  looser one.
* **Keying.** The direct peer address, or the first hop in ``X-Forwarded-For``
  when the app is deployed behind a proxy that sets it.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.infrastructure.logging import get_logger

_log = get_logger(__name__)

_WINDOW_SECONDS = 60.0
_SWEEP_THRESHOLD = 1024  # distinct keys tolerated before idle ones are reaped


class SlidingWindowLimiter:
    """Thread-safe: at most ``limit`` hits per key per rolling window."""

    def __init__(
        self,
        limit: int,
        *,
        window: float = _WINDOW_SECONDS,
        time_source: Callable[[], float] = time.monotonic,
    ) -> None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        self._limit = limit
        self._window = window
        self._time = time_source
        self._hits: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> float | None:
        """Record a hit. Returns ``None`` if allowed, else seconds until retry."""
        now = self._time()
        cutoff = now - self._window
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self._limit:
                return max(0.0, hits[0] + self._window - now)
            hits.append(now)
            if len(self._hits) > _SWEEP_THRESHOLD:
                self._sweep(cutoff)
            return None

    def _sweep(self, cutoff: float) -> None:
        """Drop keys whose window has fully expired. Caller holds the lock.

        Without this the key map grows once per distinct client address forever;
        a single sweep past a threshold keeps it proportional to *active* clients.
        """
        idle = [key for key, hits in self._hits.items() if not hits or hits[-1] <= cutoff]
        for key in idle:
            del self._hits[key]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_key(request: Request) -> str:
    """Identify the caller: the proxy's first hop if present, else the peer."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def build_rate_limit_middleware(
    *, chat_rpm: int, api_rpm: int
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    """Create the ASGI middleware callable, closing over two limiters.

    ``chat_rpm`` meters ``POST /api/chat`` (the LLM-quota spender); ``api_rpm``
    meters the rest of ``/api``. Non-``/api`` paths (``/health``, docs) are never
    limited so orchestration probes keep working under load.
    """
    chat_limiter = SlidingWindowLimiter(chat_rpm)
    api_limiter = SlidingWindowLimiter(api_rpm)

    async def rate_limit(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)

        limiter = chat_limiter if path == "/api/chat" else api_limiter
        key = client_key(request)
        retry_after = limiter.check(key)
        if retry_after is None:
            return await call_next(request)

        _log.warning("Rate limit hit: client=%s path=%s", key, path)
        seconds = max(1, int(retry_after) + 1)
        return JSONResponse(
            status_code=429,
            content={
                "detail": (
                    "Too many requests. This deployment runs on free-tier AI quota, "
                    "so requests are capped. Please retry shortly."
                )
            },
            headers={"Retry-After": str(seconds)},
        )

    return rate_limit
