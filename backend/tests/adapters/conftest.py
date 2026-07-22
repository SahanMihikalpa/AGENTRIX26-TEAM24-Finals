"""Shared fixtures for adapter tests (kept here so domain tests stay torch-free)."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from pathlib import Path

import pytest

from app.adapters.knowledge.chroma_sqlite import ChromaSqliteStore


class DeterministicEmbedder:
    """A tiny, torch-free embedder: stable hashed bag-of-words vectors.

    Satisfies ``EmbeddingProvider`` structurally and gives reproducible cosine
    rankings, so the store/seed tests never need the real model.
    """

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


@pytest.fixture
def embedder() -> DeterministicEmbedder:
    return DeterministicEmbedder()


@pytest.fixture
def store(tmp_path: Path) -> ChromaSqliteStore:
    return ChromaSqliteStore(sqlite_path=tmp_path / "kb.sqlite3", chroma_dir=tmp_path / "chroma")
