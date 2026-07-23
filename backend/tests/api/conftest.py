"""Fixtures for the API tests.

Each test gets a ``TestClient`` whose ``get_runtime`` dependency is overridden with
a fake :class:`AppRuntime`: the **real** compiled graph (so the SSE wiring is
exercised for real) built over a ``ScriptedLLM`` + a seeded ``ChromaSqliteStore`` +
``MemorySaver``. No keys, no network, no torch.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from app.adapters.knowledge.chroma_sqlite import ChromaSqliteStore
from app.adapters.knowledge.seed import KnowledgeSeeder
from app.api.main import create_app
from app.api.runtime import AppRuntime, get_runtime
from app.application.feedback import ExperienceReportIntake
from app.application.graph import GraphDependencies
from app.application.graph.builder import build_graph
from app.application.moderation import ModerationService
from app.domain.ports.source_pool import PooledDocument
from app.infrastructure.cache import InMemoryAnswerCache
from app.infrastructure.config import get_settings


class ScriptedLLM:
    """An ``LLMProvider`` that replays scripted structured outputs keyed by schema."""

    def __init__(self, structured: dict[type, Any]) -> None:
        self._structured = structured

    def complete(self, prompt: str, *, system: str | None = None, temperature: float = 0.0) -> str:
        return "ok"

    def complete_structured(
        self, prompt: str, schema: type, *, system: str | None = None, temperature: float = 0.0
    ) -> Any:
        if schema not in self._structured:
            raise AssertionError(f"no scripted response for {schema.__name__}")
        return self._structured[schema]


class DeterministicEmbedder:
    """Torch-free hashed bag-of-words embedder (``EmbeddingProvider``)."""

    @property
    def dimension(self) -> int:
        return 64

    def _vector(self, text: str) -> list[float]:
        weights = [0.0] * 64
        for token in text.lower().split():
            weights[int(hashlib.sha256(token.encode()).hexdigest(), 16) % 64] += 1.0
        norm = math.sqrt(sum(w * w for w in weights)) or 1.0
        return [w / norm for w in weights]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class FakeSourcePool:
    def __init__(self, docs: list[PooledDocument] | None = None) -> None:
        self._docs = docs or []

    def search(self, query: str, *, limit: int = 5) -> list[PooledDocument]:
        return list(self._docs[:limit])


# A small catalog: one single-variant service (no-clarify happy path), one
# multi-variant service (clarify path). Business registration is intentionally
# absent so it triggers the gap loop.
_SEED: dict[str, Any] = {
    "sources": [
        {
            "key": "src",
            "title": "Services Circular",
            "url": "https://x.gov.lk",
            "source_type": "circular",
            "retrieved_date": "2026-06-20",
            "confidence": 0.95,
            "verification_status": "verified",
        }
    ],
    "services": [
        {
            "name_en": "Passport Renewal",
            "slug": "passport_renewal",
            "category": "immigration",
            "description": "Renew a passport",
            "variants": [
                {
                    "condition_label": "standard",
                    "description": "",
                    "requirements": [
                        {"source_key": "src", "document_name": "Birth certificate"}
                    ],
                    "fees": [{"source_key": "src", "label": "Service fee", "amount_lkr": "3000"}],
                }
            ],
            "offices": [
                {
                    "name": "DIE Colombo",
                    "office_type": "other",
                    "district": "Colombo",
                    "address": "Battaramulla",
                    "hours": "9-4",
                    "contact": "011",
                }
            ],
            "chunks": [
                {"source_key": "src", "content": "passport renewal birth certificate colombo fee"}
            ],
        },
        {
            "name_en": "Land Deed Transfer",
            "slug": "land_deed_transfer",
            "category": "land",
            "description": "Transfer a land deed",
            "variants": [
                {
                    "condition_label": "inheritance",
                    "description": "",
                    "requirements": [
                        {"source_key": "src", "document_name": "Death certificate"}
                    ],
                    "fees": [{"source_key": "src", "label": "Stamp duty", "amount_lkr": "1000"}],
                },
                {"condition_label": "sale", "description": ""},
            ],
            "offices": [
                {
                    "name": "DS Galle",
                    "office_type": "DS",
                    "district": "Galle",
                    "address": "Galle Fort",
                    "hours": "9-4",
                    "contact": "091",
                }
            ],
            "chunks": [
                {"source_key": "src", "content": "land deed transfer inheritance death certificate"}
            ],
        },
    ],
}

# A factory: (structured_llm_script, pool_docs) -> (TestClient, store).
ClientFactory = Callable[..., tuple[TestClient, ChromaSqliteStore]]


@pytest.fixture
def build_client(tmp_path: Path) -> Iterator[ClientFactory]:
    clients: list[TestClient] = []

    def _build(
        structured: dict[type, Any], *, pool_docs: list[PooledDocument] | None = None
    ) -> tuple[TestClient, ChromaSqliteStore]:
        root = tmp_path / f"kb{len(clients)}"
        root.mkdir(parents=True, exist_ok=True)
        store = ChromaSqliteStore(sqlite_path=root / "kb.sqlite3", chroma_dir=root / "chroma")
        embedder = DeterministicEmbedder()
        KnowledgeSeeder(store, embedder).load(_SEED)
        llm = ScriptedLLM(structured)
        cache = InMemoryAnswerCache()
        deps = GraphDependencies(
            llm=llm,
            embedder=embedder,
            store=store,
            retriever=store,
            source_pool=FakeSourcePool(pool_docs),
            answer_cache=cache,
            web_allowlist=["gov.lk"],
            grader_sufficient_above=0.4,
        )
        runtime = AppRuntime(
            graph=build_graph(deps, checkpointer=MemorySaver()),
            store=store,
            cache=cache,
            settings=get_settings(),
            experience_intake=ExperienceReportIntake(store, llm, embedder),
            moderation=ModerationService(store, cache=cache),
        )
        app = create_app()
        app.dependency_overrides[get_runtime] = lambda: runtime
        client = TestClient(app)
        clients.append(client)
        return client, store

    yield _build
    for client in clients:
        client.close()


def parse_sse(text: str) -> list[tuple[str, dict[str, Any]]]:
    """Parse an SSE response body into ``(event, data)`` pairs."""
    events: list[tuple[str, dict[str, Any]]] = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        event = ""
        data: dict[str, Any] = {}
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data = json.loads(line[len("data:"):].strip())
        events.append((event, data))
    return events
