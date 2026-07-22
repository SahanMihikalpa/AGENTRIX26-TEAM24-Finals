"""Unit tests for the web-search adapters + the official-domain allow-list (QA-7).

Clients are injected, so these run fully offline — no Tavily key, no network.
"""

from __future__ import annotations

from typing import Any

from app.adapters.web_search.allowlist import host_allowed, normalized_domains
from app.adapters.web_search.ddg import DdgWebSearch
from app.adapters.web_search.tavily import TavilyWebSearch


def test_host_allowed_matches_domain_and_subdomains() -> None:
    allow = ["gov.lk"]
    assert host_allowed("https://www.rgd.gov.lk/nic", allow)
    assert host_allowed("https://gov.lk", allow)


def test_host_allowed_rejects_outsiders_and_lookalikes() -> None:
    allow = ["gov.lk"]
    assert not host_allowed("https://spam.com/gov.lk", allow)
    assert not host_allowed("https://fakegov.lk/x", allow)  # ends with gov.lk but not a subdomain
    assert not host_allowed("not a url", allow)


def test_normalized_domains_cleans_entries() -> None:
    assert normalized_domains([" .GOV.LK ", "", "rgd.gov.lk"]) == ["gov.lk", "rgd.gov.lk"]


class _FakeTavilyClient:
    def __init__(self, results: list[dict[str, Any]]) -> None:
        self._results = results
        self.last_kwargs: dict[str, Any] = {}

    def search(self, **kwargs: Any) -> dict[str, Any]:
        self.last_kwargs = kwargs
        return {"results": self._results}


def test_tavily_filters_to_allowlist_and_maps_fields() -> None:
    client = _FakeTavilyClient(
        [
            {"title": "RGD", "url": "https://rgd.gov.lk/nic", "content": "snippet"},
            {"title": "Spam", "url": "https://spam.com/x", "content": "no"},
        ]
    )
    search = TavilyWebSearch("key", client=client)

    results = search.search("nic", allowlist=["gov.lk"], max_results=5)

    assert [r.url for r in results] == ["https://rgd.gov.lk/nic"]
    assert results[0].title == "RGD"
    assert results[0].snippet == "snippet"
    assert client.last_kwargs["include_domains"] == ["gov.lk"]
    assert client.last_kwargs["max_results"] == 5


class _FakeDdgsClient:
    def __init__(self, results: list[dict[str, Any]]) -> None:
        self._results = results
        self.last_query = ""

    def text(self, query: str, max_results: int) -> list[dict[str, Any]]:
        self.last_query = query
        return self._results[:max_results]


def test_ddg_scopes_query_filters_and_caps_results() -> None:
    client = _FakeDdgsClient(
        [
            {"title": "A", "href": "https://a.gov.lk/1", "body": "b1"},
            {"title": "B", "href": "https://b.com/2", "body": "b2"},
            {"title": "C", "href": "https://c.gov.lk/3", "body": "b3"},
            {"title": "D", "href": "https://d.gov.lk/4", "body": "b4"},
        ]
    )
    search = DdgWebSearch(client=client)

    results = search.search("passport", allowlist=["gov.lk"], max_results=2)

    assert [r.url for r in results] == ["https://a.gov.lk/1", "https://c.gov.lk/3"]
    assert "site:gov.lk" in client.last_query
    assert results[0].snippet == "b1"
