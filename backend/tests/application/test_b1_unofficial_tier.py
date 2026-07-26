"""B1's second-tier search, and the guarantee that what it finds is not served.

Some requests simply have no page on a government domain, and the allow-listed
search then returns nothing — a dead end. Tier 2 searches wider so the gap loop has
something to work with; the safety property is that those findings reach a
*moderator*, never a citizen's checklist.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.application.agents.b1_research import ResearchAgent
from app.application.agents.b3_kb_updater import KBUpdaterAgent
from app.application.graph.state import new_state
from app.domain.entities import VerificationStatus
from app.domain.ports.web_search import WebResult
from tests.application.conftest import DeterministicEmbedder, FakeSourcePool, SeededKB


class RecordingWebSearch:
    """A ``WebSearch`` that answers per tier and records how it was called."""

    def __init__(
        self, *, official: list[WebResult] | None = None, wider: list[WebResult] | None = None
    ) -> None:
        self._official = official or []
        self._wider = wider or []
        self.calls: list[bool] = []  # the `unrestricted` flag of each call

    def search(
        self,
        query: str,
        *,
        allowlist: Sequence[str],
        max_results: int = 5,
        unrestricted: bool = False,
    ) -> list[WebResult]:
        self.calls.append(unrestricted)
        return list(self._wider if unrestricted else self._official)


def _state() -> dict:
    state = new_state("s1", "how do I get a widget permit")
    state["intent"] = {"normalized_query": "widget permit"}
    return state


_OFFICIAL = WebResult(title="Official", url="https://x.gov.lk/a", snippet="official text")
_WIDER = WebResult(title="Blog", url="https://blog.example.com/a", snippet="blog text")


def test_tier_two_is_not_reached_when_official_results_exist() -> None:
    web = RecordingWebSearch(official=[_OFFICIAL], wider=[_WIDER])
    agent = ResearchAgent(
        FakeSourcePool(), web, allowlist=["gov.lk"], allow_unofficial_fallback=True
    )

    buffer = agent(_state())["acquisition_buffer"]

    assert web.calls == [False], "the wider search must not run"
    assert [entry["official"] for entry in buffer] == [True]


def test_tier_two_runs_only_when_the_allowlisted_search_is_empty() -> None:
    web = RecordingWebSearch(official=[], wider=[_WIDER])
    agent = ResearchAgent(
        FakeSourcePool(), web, allowlist=["gov.lk"], allow_unofficial_fallback=True
    )

    buffer = agent(_state())["acquisition_buffer"]

    assert web.calls == [False, True]
    assert [entry["official"] for entry in buffer] == [False]
    assert buffer[0]["url"] == "https://blog.example.com/a"


def test_tier_two_is_off_by_default() -> None:
    """QA-7 must not relax because a call site forgot a parameter."""
    web = RecordingWebSearch(official=[], wider=[_WIDER])
    agent = ResearchAgent(FakeSourcePool(), web, allowlist=["gov.lk"])

    buffer = agent(_state())["acquisition_buffer"]

    assert web.calls == [False]
    assert buffer == []


def test_pool_documents_are_official() -> None:
    from app.domain.entities import SourceType
    from app.domain.ports.source_pool import PooledDocument

    pool = FakeSourcePool(
        [
            PooledDocument(
                title="Circular",
                text="pool text",
                url=None,
                source_type=SourceType.CIRCULAR,
                published_date=None,
            )
        ]
    )
    agent = ResearchAgent(pool, RecordingWebSearch(), allowlist=["gov.lk"])

    buffer = agent(_state())["acquisition_buffer"]

    assert [entry["official"] for entry in buffer] == [True]


# ── the safety property: unofficial findings cannot be served ────
def _curated(*, official: bool) -> dict:
    """A B2 record, in the shape B3 actually consumes."""
    return {
        "text": "some extracted guidance about the widget permit",
        "source": {
            "title": "Official" if official else "Blog",
            "url": "https://x.gov.lk/a" if official else "https://blog.example.com/a",
            "source_type": "portal",
            "published_date": None,
            "retrieved_date": "2026-07-22",
            "confidence": 0.95,  # B2 was very confident — it must not matter
            "verification_status": "auto_gathered",
            "origin": "web",
            "official": official,
        },
        "extraction": {
            "service_name": "Widget Permit",
            "service_slug": "widget-permit",
            "category": "",
            "description": "",
            "condition_label": "standard",
            "requirements": [{"document_name": "Application form", "is_mandatory": True}],
            "fees": [],
            "offices": [],
            "district": "",
            "extraction_confidence": 0.95,
        },
    }


def test_an_unofficial_source_is_capped_below_the_serving_threshold(kb: SeededKB) -> None:
    state = new_state("s1", "widget permit")
    state["curated"] = [_curated(official=False)]
    KBUpdaterAgent(kb.store, DeterministicEmbedder(), unofficial_max_confidence=0.5)(state)

    source = next(
        s for s in kb.store.list_sources_for_moderation() if s.url == "https://blog.example.com/a"
    )

    assert source.is_official is False
    assert source.confidence == 0.5, "capped, however confident the extraction was"
    assert source.confidence < 0.6, "below the default serving threshold, so A6 gates it"
    assert source.verification_status == VerificationStatus.AUTO_GATHERED


def test_an_official_source_keeps_its_extraction_confidence(kb: SeededKB) -> None:
    state = new_state("s1", "widget permit")
    state["curated"] = [_curated(official=True)]
    KBUpdaterAgent(kb.store, DeterministicEmbedder(), unofficial_max_confidence=0.5)(state)

    source = next(
        s for s in kb.store.list_sources_for_moderation() if s.url == "https://x.gov.lk/a"
    )

    assert source.is_official is True
    assert source.confidence == 0.95


def test_unofficial_sources_appear_in_the_moderation_queue(kb: SeededKB) -> None:
    """That queue is the whole point: a human decides, not the crawler."""
    state = new_state("s1", "widget permit")
    state["curated"] = [_curated(official=False)]
    KBUpdaterAgent(kb.store, DeterministicEmbedder())(state)

    queued = kb.store.list_sources_for_moderation()

    assert any(not source.is_official for source in queued)


# ── web PDF fetch (full document, not just the snippet) ──────────
class FakePdfFetcher:
    """A DocumentFetcher that returns parsed text for .pdf URLs it is told about."""

    def __init__(self, by_url: dict[str, str]) -> None:
        self._by_url = by_url
        self.fetched: list[str] = []

    def fetch(self, url: str):
        from app.domain.entities import SourceType
        from app.domain.ports.parser import ParsedDocument

        self.fetched.append(url)
        text = self._by_url.get(url)
        if text is None:
            return None
        return ParsedDocument(text=text, source_type=SourceType.CIRCULAR, title="Gazette PDF")


def test_a_web_pdf_is_ingested_in_full_not_as_a_snippet() -> None:
    pdf_url = "https://dmt.gov.lk/downloads/licence.pdf"
    web = RecordingWebSearch(
        official=[WebResult(title="Licence", url=pdf_url, snippet="short preview")]
    )
    fetcher = FakePdfFetcher({pdf_url: "FULL PDF TEXT: bring your NIC, medical report, and fee."})
    agent = ResearchAgent(
        FakeSourcePool(), web, allowlist=["gov.lk"], document_fetcher=fetcher
    )

    entry = agent(_state())["acquisition_buffer"][0]

    assert fetcher.fetched == [pdf_url]
    assert entry["text"].startswith("FULL PDF TEXT")
    assert entry["text"] != "short preview"
    assert entry["source_type"] == "circular"  # from the parsed PDF, not the default portal
    assert entry["title"] == "Gazette PDF"


def test_a_failed_pdf_fetch_falls_back_to_the_snippet() -> None:
    pdf_url = "https://dmt.gov.lk/missing.pdf"
    web = RecordingWebSearch(
        official=[WebResult(title="Licence", url=pdf_url, snippet="the snippet")]
    )
    fetcher = FakePdfFetcher({})  # knows about no urls -> returns None
    agent = ResearchAgent(
        FakeSourcePool(), web, allowlist=["gov.lk"], document_fetcher=fetcher
    )

    entry = agent(_state())["acquisition_buffer"][0]

    assert entry["text"] == "the snippet"


def test_without_a_fetcher_the_snippet_is_used() -> None:
    web = RecordingWebSearch(
        official=[WebResult(title="Licence", url="https://x.gov.lk/a.pdf", snippet="the snippet")]
    )
    agent = ResearchAgent(FakeSourcePool(), web, allowlist=["gov.lk"])

    entry = agent(_state())["acquisition_buffer"][0]

    assert entry["text"] == "the snippet"


# ── gazette priority tier (official legal sources first) ─────────
class TieredWebSearch:
    """Returns results keyed by the allowlist it was called with; records calls."""

    def __init__(self, by_allowlist: dict[str, list[WebResult]]) -> None:
        self._by = by_allowlist
        self.calls: list[tuple[tuple[str, ...], bool]] = []

    def search(self, query, *, allowlist, max_results=5, unrestricted=False):
        key = ",".join(allowlist)
        self.calls.append((tuple(allowlist), unrestricted))
        return list(self._by.get(key, []))


def test_both_tiers_are_queried_and_gazette_reads_first() -> None:
    gaz = WebResult(title="Gazette", url="https://documents.gov.lk/a.pdf", snippet="act")
    gen = WebResult(title="Portal", url="https://dmt.gov.lk/x", snippet="page")
    web = TieredWebSearch({"documents.gov.lk": [gaz], "gov.lk": [gen]})
    agent = ResearchAgent(
        FakeSourcePool(), web, allowlist=["gov.lk"], priority_domains=["documents.gov.lk"]
    )

    buffer = agent(_state())["acquisition_buffer"]

    # Both tiers are queried (order of the calls is an internal detail)...
    assert {a for a, _ in web.calls} == {("gov.lk",), ("documents.gov.lk",)}
    # ...and the gazette result is prepended so it reads first.
    assert [e["url"] for e in buffer] == [
        "https://documents.gov.lk/a.pdf",
        "https://dmt.gov.lk/x",
    ]
    assert all(e["official"] for e in buffer)


def test_a_result_in_both_tiers_is_not_duplicated() -> None:
    shared = WebResult(title="Act", url="https://documents.gov.lk/a.pdf", snippet="act")
    web = TieredWebSearch({"documents.gov.lk": [shared], "gov.lk": [shared]})
    agent = ResearchAgent(
        FakeSourcePool(), web, allowlist=["gov.lk"], priority_domains=["documents.gov.lk"]
    )

    buffer = agent(_state())["acquisition_buffer"]

    assert [e["url"] for e in buffer] == ["https://documents.gov.lk/a.pdf"]


def test_without_priority_domains_only_the_allowlist_is_searched() -> None:
    gen = WebResult(title="Portal", url="https://dmt.gov.lk/x", snippet="page")
    web = TieredWebSearch({"gov.lk": [gen]})
    agent = ResearchAgent(FakeSourcePool(), web, allowlist=["gov.lk"])

    buffer = agent(_state())["acquisition_buffer"]

    assert [c[0] for c in web.calls] == [("gov.lk",)]
    assert [e["url"] for e in buffer] == ["https://dmt.gov.lk/x"]


def test_priority_tier_adds_gazette_on_top_without_crowding_out_portals() -> None:
    """General portals keep their full budget; a few gazette hits come on top."""
    gaz = [WebResult(title=f"G{i}", url=f"https://documents.gov.lk/{i}.pdf", snippet="act")
           for i in range(5)]
    gen = [WebResult(title=f"P{i}", url=f"https://immigration.gov.lk/{i}", snippet="page")
           for i in range(5)]
    web = TieredWebSearch({"documents.gov.lk": gaz, "gov.lk": gen})
    agent = ResearchAgent(
        FakeSourcePool(), web, allowlist=["gov.lk"],
        priority_domains=["documents.gov.lk"], max_results=5,
    )

    buffer = agent(_state())["acquisition_buffer"]

    # 5 general portals + up to floor(5/2)=2 gazette on top, both hosts present.
    assert sum("immigration.gov.lk" in e["url"] for e in buffer) == 5
    assert sum("documents.gov.lk" in e["url"] for e in buffer) == 2
    assert "documents.gov.lk" in buffer[0]["url"]  # gazette reads first


def test_priority_tier_that_only_repeats_general_adds_nothing() -> None:
    """When the gazette results are already in the general set, no duplicates."""
    shared = [WebResult(title="Act", url="https://documents.gov.lk/a.pdf", snippet="act")]
    web = TieredWebSearch({"documents.gov.lk": shared, "gov.lk": shared})
    agent = ResearchAgent(
        FakeSourcePool(), web, allowlist=["gov.lk"], priority_domains=["documents.gov.lk"]
    )

    buffer = agent(_state())["acquisition_buffer"]

    assert [e["url"] for e in buffer] == ["https://documents.gov.lk/a.pdf"]
