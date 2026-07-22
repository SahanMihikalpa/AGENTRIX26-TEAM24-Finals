"""``EmbeddingProvider`` port — local text→vector embedding.

Implemented by ``adapters/embeddings/bge.py`` (local ``bge-base-en-v1.5``).
Query and document embedding are kept distinct because asymmetric models (BGE)
prepend different instructions to each; the **same** model must be used at write
(B3) and read (A4) — the embedding invariant (AD-4).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """A swappable, local-first embedding backend."""

    @property
    def dimension(self) -> int:
        """Dimensionality of the produced vectors (must match the vector store)."""
        ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed passages for storage (B3)."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query for retrieval (A4)."""
        ...
