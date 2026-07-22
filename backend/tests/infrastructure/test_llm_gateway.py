"""Unit tests for the rate-limited LLM gateway: throttle, retry, fallback (AD-10).

A fake clock makes the token bucket and back-off deterministic — no real time
passes — and scripted providers drive the retry/fallback paths.
"""

from __future__ import annotations

import pytest

from app.domain.ports.llm import LLMProvider
from app.infrastructure.llm_gateway import LLMGateway, TokenBucket


class _FakeClock:
    """A controllable monotonic clock; ``sleep`` advances it (and records waits)."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class _DummySchema:
    pass


class _ScriptedProvider:
    """An ``LLMProvider`` that fails a scripted number of times, then succeeds."""

    def __init__(
        self, *, answer: str = "ok", failures: int = 0, error: Exception | None = None
    ) -> None:
        self._answer = answer
        self._remaining_failures = failures
        self._always_error = error
        self.calls = 0

    def complete(self, prompt: str, *, system: str | None = None, temperature: float = 0.0) -> str:
        self.calls += 1
        if self._always_error is not None:
            raise self._always_error
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise RuntimeError("transient")
        return self._answer

    def complete_structured(
        self,
        prompt: str,
        schema: type[object],
        *,
        system: str | None = None,
        temperature: float = 0.0,
    ) -> object:
        self.calls += 1
        return schema()


def test_gateway_satisfies_port() -> None:
    assert isinstance(LLMGateway(_ScriptedProvider()), LLMProvider)


def test_token_bucket_throttles_after_capacity_is_spent() -> None:
    clock = _FakeClock()
    bucket = TokenBucket(60, time_source=clock.time, sleep=clock.sleep)  # 1 token/sec, cap 60

    for _ in range(60):
        bucket.acquire()
    assert clock.sleeps == []  # capacity covers the burst

    bucket.acquire()  # the 61st must wait ~1s for a refill
    assert clock.sleeps[0] == pytest.approx(1.0, abs=0.01)


def test_retry_then_success_uses_exponential_backoff() -> None:
    provider = _ScriptedProvider(answer="done", failures=2)
    clock = _FakeClock()
    gateway = LLMGateway(
        provider,
        rate_limit_rpm=600,
        max_retries=3,
        backoff_base_seconds=0.5,
        sleep=clock.sleep,
        time_source=clock.time,
    )

    assert gateway.complete("q") == "done"
    assert provider.calls == 3  # 2 failures + 1 success
    assert clock.sleeps == [0.5, 1.0]  # back-off after each failure


def test_exhausted_retries_raise_when_no_fallback() -> None:
    provider = _ScriptedProvider(error=RuntimeError("always down"))
    clock = _FakeClock()
    gateway = LLMGateway(
        provider, rate_limit_rpm=600, max_retries=1, sleep=clock.sleep, time_source=clock.time
    )

    with pytest.raises(RuntimeError, match="always down"):
        gateway.complete("q")
    assert provider.calls == 2  # initial + 1 retry


def test_falls_back_to_secondary_on_primary_failure() -> None:
    primary = _ScriptedProvider(error=RuntimeError("primary down"))
    fallback = _ScriptedProvider(answer="from fallback")
    clock = _FakeClock()
    gateway = LLMGateway(
        primary,
        fallback=fallback,
        rate_limit_rpm=600,
        max_retries=1,
        sleep=clock.sleep,
        time_source=clock.time,
    )

    assert gateway.complete("q") == "from fallback"
    assert primary.calls == 2  # primary exhausted its retries first
    assert fallback.calls == 1


def test_complete_structured_is_delegated() -> None:
    gateway = LLMGateway(_ScriptedProvider())
    assert isinstance(gateway.complete_structured("q", _DummySchema), _DummySchema)
