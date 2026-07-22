"""Central, rate-limited LLM gateway (AD-10).

Every agent calls Gemini/Groq through this one choke point so the whole
multi-agent system stays under the free-tier ceiling. It is a **decorator** over
the :class:`~app.domain.ports.llm.LLMProvider` port — it *is* an ``LLMProvider``
itself, so agents depend on the port and never know the gateway is there.

Three responsibilities, in order:

1. **Throttle** — a thread-safe token bucket caps requests/minute (default 15).
2. **Retry** — transient failures are retried with exponential backoff.
3. **Fall back** — if the primary provider keeps failing, switch to the
   secondary (Groq) and retry there before giving up.

Retry is intentionally **provider-agnostic**: we retry on any exception rather
than import provider-specific error types, which would leak an adapter detail
into infrastructure. The trade-off (occasionally retrying a non-transient error)
is bounded by ``max_retries`` and accepted for a clean hexagonal boundary.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import TypeVar

from app.domain.ports.llm import LLMProvider
from app.infrastructure.logging import get_logger

T = TypeVar("T")
R = TypeVar("R")

_log = get_logger(__name__)


class TokenBucket:
    """A thread-safe token bucket: at most ``rate_per_minute`` acquisitions/min.

    The clock and sleep are injectable so the limiter is deterministically
    testable without real time passing.
    """

    def __init__(
        self,
        rate_per_minute: int,
        *,
        capacity: int | None = None,
        time_source: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if rate_per_minute <= 0:
            raise ValueError("rate_per_minute must be positive")
        self._capacity = float(capacity if capacity is not None else rate_per_minute)
        self._tokens = self._capacity
        self._refill_per_sec = rate_per_minute / 60.0
        self._time = time_source
        self._sleep = sleep
        self._updated_at = time_source()
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> None:
        """Block until ``tokens`` are available, then consume them."""
        while True:
            with self._lock:
                now = self._time()
                elapsed = now - self._updated_at
                self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_per_sec)
                self._updated_at = now
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                wait = (tokens - self._tokens) / self._refill_per_sec
            self._sleep(wait)


class LLMGateway:
    """Rate-limited, retrying, failover ``LLMProvider`` over one or two backends."""

    def __init__(
        self,
        primary: LLMProvider,
        *,
        fallback: LLMProvider | None = None,
        rate_limit_rpm: int = 15,
        max_retries: int = 2,
        backoff_base_seconds: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
        time_source: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        self._primary = primary
        self._fallback = fallback
        self._bucket = TokenBucket(rate_limit_rpm, time_source=time_source, sleep=sleep)
        self._max_retries = max_retries
        self._backoff_base = backoff_base_seconds
        self._sleep = sleep

    def complete(
        self, prompt: str, *, system: str | None = None, temperature: float = 0.0
    ) -> str:
        return self._run(
            lambda provider: provider.complete(prompt, system=system, temperature=temperature)
        )

    def complete_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        system: str | None = None,
        temperature: float = 0.0,
    ) -> T:
        return self._run(
            lambda provider: provider.complete_structured(
                prompt, schema, system=system, temperature=temperature
            )
        )

    # ── internals ────────────────────────────────────────────────
    def _run(self, call: Callable[[LLMProvider], R]) -> R:
        """Run ``call`` against the primary; fail over to the fallback if needed."""
        try:
            return self._attempt(self._primary, call)
        except Exception as primary_error:
            if self._fallback is None:
                raise
            _log.warning(
                "primary LLM provider failed (%s); falling back to secondary",
                primary_error,
            )
            return self._attempt(self._fallback, call)

    def _attempt(self, provider: LLMProvider, call: Callable[[LLMProvider], R]) -> R:
        """Call ``provider`` with rate-limiting + bounded exponential-backoff retry."""
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            self._bucket.acquire()
            try:
                return call(provider)
            except Exception as error:
                last_error = error
                if attempt < self._max_retries:
                    backoff = self._backoff_base * (2**attempt)
                    _log.warning(
                        "LLM call failed (attempt %d/%d): %s; retrying in %.2fs",
                        attempt + 1,
                        self._max_retries + 1,
                        error,
                        backoff,
                    )
                    self._sleep(backoff)
        assert last_error is not None  # the loop runs at least once
        raise last_error
