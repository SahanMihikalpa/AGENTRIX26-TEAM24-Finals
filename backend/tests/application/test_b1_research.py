"""B1 · Research — local-pool-first, web-fallback evidence gathering."""

from __future__ import annotations

from app.application.agents.b1_research import ResearchAgent
from app.application.graph.state import GraphState, new_state
from app.domain.entities import SourceType
from app.domain.ports.source_pool import PooledDocument
from app.domain.ports.web_search import WebResult
from tests.application.conftest import FakeSourcePool, FakeWebSearch


def _state(query: str = "register a business name") -> GraphState:
    state = new_state("s", query)
    state["intent"] = {"normalized_query": query, "service_guess": "business_name_registration"}
    return state


def test_uses_local_pool_first_and_skips_web_when_satisfied() -> None:
    pool = FakeSourcePool(
        [PooledDocument(text="business reg", title="Circular", source_type=SourceType.CIRCULAR)]
    )
    web = FakeWebSearch([WebResult(title="x", url="https://x.gov.lk", snippet="...")])
    agent = ResearchAgent(pool, web, allowlist=["gov.lk"])

    buffer = agent(_state())["acquisition_buffer"]

    assert [entry["origin"] for entry in buffer] == ["pool"]
    assert web.last_allowlist == []  # web never queried — the pool was enough


def test_falls_back_to_web_when_pool_is_empty() -> None:
    pool = FakeSourcePool([])
    web = FakeWebSearch(
        [WebResult(title="DMT page", url="https://dmt.gov.lk/biz", snippet="how to register")]
    )
    agent = ResearchAgent(pool, web, allowlist=["gov.lk"])

    buffer = agent(_state())["acquisition_buffer"]

    assert [entry["origin"] for entry in buffer] == ["web"]
    assert buffer[0]["url"] == "https://dmt.gov.lk/biz"
    assert buffer[0]["text"] == "how to register"
    assert web.last_allowlist == ["gov.lk"]  # allow-list enforced (QA-7)


def test_combines_pool_and_web_below_min_local_results() -> None:
    pool = FakeSourcePool(
        [PooledDocument(text="thin", title="Thin", source_type=SourceType.PORTAL)]
    )
    web = FakeWebSearch([WebResult(title="more", url="https://x.gov.lk", snippet="more detail")])
    agent = ResearchAgent(pool, web, allowlist=["gov.lk"], min_local_results=2)

    buffer = agent(_state())["acquisition_buffer"]

    assert {entry["origin"] for entry in buffer} == {"pool", "web"}


def test_no_web_provider_yields_pool_only() -> None:
    agent = ResearchAgent(FakeSourcePool([]))

    buffer = agent(_state())["acquisition_buffer"]

    assert buffer == []  # nothing found → supervisor will route to fallback
