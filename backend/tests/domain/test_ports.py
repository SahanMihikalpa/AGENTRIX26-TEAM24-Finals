"""The ports are structural contracts — verify a minimal fake satisfies each.

These fakes also document the expected shape of every adapter and double as the
test doubles used by the agent unit tests in Stage 4.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.domain.entities import SourceType
from app.domain.ports import (
    AnswerCache,
    EmbeddingProvider,
    KnowledgeStore,
    LLMProvider,
    ParsedDocument,
    PooledDocument,
    Retriever,
    SourceParser,
    SourcePool,
    WebResult,
    WebSearch,
)


class FakeLLM:
    def complete(self, prompt: str, *, system: str | None = None, temperature: float = 0.0) -> str:
        return "ok"

    def complete_structured(
        self,
        prompt: str,
        schema: type,
        *,
        system: str | None = None,
        temperature: float = 0.0,
    ) -> object:
        return schema()


class FakeEmbeddings:
    dimension = 3

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [[0.0] * self.dimension for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * self.dimension


class FakeKnowledgeStore:
    def add_service(self, service: object) -> object:
        return service

    def add_variant(self, variant: object) -> object:
        return variant

    def add_requirement(self, requirement: object) -> object:
        return requirement

    def add_fee(self, fee: object) -> object:
        return fee

    def add_office(self, office: object) -> object:
        return office

    def link_service_office(self, service_id: int, office_id: int) -> None:
        return None

    def add_district_variation(self, variation: object) -> object:
        return variation

    def source_exists(self, *, url: str | None, content_hash: str) -> bool:
        return False

    def upsert_source(self, source: object, *, content_hash: str | None = None) -> object:
        return source

    def upsert_chunks(self, chunks: object, embeddings: object) -> None:
        return None

    def find_services(self, query: str, *, limit: int = 5) -> list:
        return []

    def get_service(self, service_id: int) -> object | None:
        return None

    def list_variants(self, service_id: int) -> list:
        return []

    def get_requirements(self, variant_id: int) -> list:
        return []

    def get_fees(self, variant_id: int) -> list:
        return []

    def get_offices(self, service_id: int, *, district: str | None = None) -> list:
        return []

    def add_experience_report(self, report: object) -> object:
        return report

    def list_sources_for_moderation(self, *, limit: int = 50) -> list:
        return []

    def set_source_verification_status(
        self, source_id: int, status: object
    ) -> object | None:
        return None

    def delete_chunks_for_source(self, source_id: int) -> int:
        return 0

    def get_service_ids_for_source(self, source_id: int) -> list:
        return []


class FakeAnswerCache:
    def get_answer(
        self, service_id: int, *, variant_id: int | None = None, district: str | None = None
    ) -> dict | None:
        return None

    def put_answer(
        self,
        service_id: int,
        answer: dict,
        *,
        variant_id: int | None = None,
        district: str | None = None,
    ) -> None:
        return None

    def invalidate_service(self, service_id: int) -> None:
        return None


class FakeRetriever:
    def search(
        self,
        query_embedding: Sequence[float],
        *,
        filters: Mapping[str, object] | None = None,
        top_k: int = 5,
    ) -> list:
        return []


class FakeWebSearch:
    def search(self, query: str, *, allowlist: Sequence[str], max_results: int = 5) -> list:
        return []


class FakeParser:
    def parse_pdf(self, data: bytes, *, url: str | None = None) -> ParsedDocument:
        return ParsedDocument(text="", source_type=SourceType.PORTAL)

    def parse_html(self, html: str, *, url: str | None = None) -> ParsedDocument:
        return ParsedDocument(text="", source_type=SourceType.PORTAL)


class FakeSourcePool:
    def search(self, query: str, *, limit: int = 5) -> list:
        return []


def test_fakes_satisfy_ports() -> None:
    assert isinstance(FakeLLM(), LLMProvider)
    assert isinstance(FakeEmbeddings(), EmbeddingProvider)
    assert isinstance(FakeKnowledgeStore(), KnowledgeStore)
    assert isinstance(FakeAnswerCache(), AnswerCache)
    assert isinstance(FakeRetriever(), Retriever)
    assert isinstance(FakeWebSearch(), WebSearch)
    assert isinstance(FakeParser(), SourceParser)
    assert isinstance(FakeSourcePool(), SourcePool)


def test_pooled_document_is_a_value_object() -> None:
    doc = PooledDocument(text="...", title="Circular", source_type=SourceType.CIRCULAR)
    assert doc.url is None and doc.title == "Circular"


def test_web_result_is_a_value_object() -> None:
    result = WebResult(title="Title", url="https://dmt.gov.lk", snippet="...")
    assert result.url.endswith("gov.lk")
