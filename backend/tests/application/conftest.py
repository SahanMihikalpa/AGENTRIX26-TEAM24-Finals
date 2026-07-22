"""Shared fixtures for the agent (application-layer) tests.

The agents depend only on the **ports**, so they are exercised here with two kinds
of doubles:

* ``ScriptedLLM`` — a tiny ``LLMProvider`` that returns pre-built structured
  objects, so LLM agents are deterministic and need no network/torch.
* A real ``ChromaSqliteStore`` seeded with a tiny catalog via ``KnowledgeSeeder``
  — high-fidelity for the retrieval/identify/clarify/action-pack agents that read
  the store, while still fast (torch-free ``DeterministicEmbedder``).
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from app.adapters.knowledge.chroma_sqlite import ChromaSqliteStore
from app.adapters.knowledge.seed import KnowledgeSeeder
from app.domain.ports.source_pool import PooledDocument
from app.domain.ports.web_search import WebResult


class ScriptedLLM:
    """An ``LLMProvider`` that replays scripted structured/text responses."""

    def __init__(
        self, *, structured: dict[type, Any] | None = None, text: str = "ok"
    ) -> None:
        self._structured = structured or {}
        self._text = text
        self.calls: list[tuple[str, str]] = []

    def complete(self, prompt: str, *, system: str | None = None, temperature: float = 0.0) -> str:
        self.calls.append(("complete", prompt))
        return self._text

    def complete_structured(
        self,
        prompt: str,
        schema: type,
        *,
        system: str | None = None,
        temperature: float = 0.0,
    ) -> Any:
        self.calls.append(("structured", schema.__name__))
        if schema not in self._structured:
            raise AssertionError(f"ScriptedLLM has no scripted response for {schema.__name__}")
        return self._structured[schema]


class FakeSourcePool:
    """A ``SourcePool`` that returns a fixed list of pooled documents."""

    def __init__(self, docs: list[PooledDocument] | None = None) -> None:
        self._docs = docs or []

    def search(self, query: str, *, limit: int = 5) -> list[PooledDocument]:
        return list(self._docs[:limit])


class FakeWebSearch:
    """A ``WebSearch`` that records the allow-list it was called with and replays hits."""

    def __init__(self, results: list[WebResult] | None = None) -> None:
        self._results = results or []
        self.last_allowlist: list[str] = []

    def search(
        self, query: str, *, allowlist: Sequence[str], max_results: int = 5
    ) -> list[WebResult]:
        self.last_allowlist = list(allowlist)
        return list(self._results[:max_results])


class DeterministicEmbedder:
    """Torch-free, reproducible hashed bag-of-words embedder (``EmbeddingProvider``)."""

    def __init__(self, dim: int = 64) -> None:
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def _vector(self, text: str) -> list[float]:
        weights = [0.0] * self._dim
        for token in text.lower().split():
            bucket = int(hashlib.sha256(token.encode()).hexdigest(), 16) % self._dim
            weights[bucket] += 1.0
        norm = math.sqrt(sum(weight * weight for weight in weights)) or 1.0
        return [weight / norm for weight in weights]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@dataclass(frozen=True)
class SeededKB:
    """A seeded store plus the ids the tests assert against."""

    store: ChromaSqliteStore
    deed_service_id: int
    inheritance_variant_id: int
    sale_variant_id: int
    survey_service_id: int
    survey_variant_id: int


_SEED: dict[str, Any] = {
    "sources": [
        {
            "key": "deed_circular",
            "title": "Land Registry Circular 2024",
            "url": "https://landregistry.gov.lk/circular",
            "source_type": "circular",
            "retrieved_date": "2026-06-20",
            "confidence": 0.95,
            "verification_status": "verified",
        }
    ],
    "services": [
        {
            "name_en": "Land Deed Transfer",
            "slug": "land_deed_transfer",
            "category": "land",
            "description": "Transfer ownership of a land deed",
            "variants": [
                {
                    "condition_label": "inheritance",
                    "description": "Transfer by inheritance",
                    "requirements": [
                        {
                            "source_key": "deed_circular",
                            "document_name": "Death certificate",
                            "is_mandatory": True,
                        }
                    ],
                    "fees": [
                        {"source_key": "deed_circular", "label": "Stamp duty", "amount_lkr": "1000"}
                    ],
                },
                {
                    "condition_label": "sale",
                    "description": "Transfer by sale",
                    "requirements": [
                        {
                            "source_key": "deed_circular",
                            "document_name": "Sale agreement",
                            "is_mandatory": True,
                        }
                    ],
                    "fees": [
                        {"source_key": "deed_circular", "label": "Stamp duty", "amount_lkr": "4000"}
                    ],
                },
            ],
            "offices": [
                {
                    "name": "DS Galle",
                    "office_type": "DS",
                    "district": "Galle",
                    "address": "Galle Fort",
                    "hours": "9-4",
                    "contact": "091-1234567",
                }
            ],
            "chunks": [
                {
                    "source_key": "deed_circular",
                    "content": "land deed transfer inheritance death certificate stamp duty Galle",
                }
            ],
        },
        {
            "name_en": "Land Survey Request",
            "slug": "land_survey",
            "category": "land",
            "description": "Request an official land survey",
            "variants": [{"condition_label": "standard", "description": "Standard survey"}],
            "chunks": [
                {"source_key": "deed_circular", "content": "land survey request measurement"}
            ],
        },
    ],
}


@pytest.fixture
def embedder() -> DeterministicEmbedder:
    return DeterministicEmbedder()


@pytest.fixture
def kb(tmp_path: Path, embedder: DeterministicEmbedder) -> SeededKB:
    store = ChromaSqliteStore(
        sqlite_path=tmp_path / "kb.sqlite3", chroma_dir=tmp_path / "chroma"
    )
    KnowledgeSeeder(store, embedder).load(_SEED)

    deed = store.find_services("land_deed_transfer")[0]
    survey = store.find_services("land_survey")[0]
    assert deed.id is not None and survey.id is not None
    variants = {v.condition_label: v for v in store.list_variants(deed.id)}
    survey_variant = store.list_variants(survey.id)[0]
    assert variants["inheritance"].id is not None and variants["sale"].id is not None
    assert survey_variant.id is not None

    return SeededKB(
        store=store,
        deed_service_id=deed.id,
        inheritance_variant_id=variants["inheritance"].id,
        sale_variant_id=variants["sale"].id,
        survey_service_id=survey.id,
        survey_variant_id=survey_variant.id,
    )
