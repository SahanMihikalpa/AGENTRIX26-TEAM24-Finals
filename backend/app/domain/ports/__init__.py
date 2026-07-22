"""Domain ports — the hexagon's sockets (interfaces only, no implementations)."""

from app.domain.ports.cache import AnswerCache
from app.domain.ports.embeddings import EmbeddingProvider
from app.domain.ports.knowledge import KnowledgeStore, Retriever
from app.domain.ports.llm import LLMProvider
from app.domain.ports.parser import ParsedDocument, SourceParser
from app.domain.ports.source_pool import PooledDocument, SourcePool
from app.domain.ports.web_search import WebResult, WebSearch

__all__ = [
    "AnswerCache",
    "EmbeddingProvider",
    "KnowledgeStore",
    "LLMProvider",
    "ParsedDocument",
    "PooledDocument",
    "Retriever",
    "SourceParser",
    "SourcePool",
    "WebResult",
    "WebSearch",
]
