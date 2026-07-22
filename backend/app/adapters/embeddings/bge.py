"""Local bge embeddings adapter (``EmbeddingProvider``).

Wraps sentence-transformers ``BAAI/bge-base-en-v1.5``. The model is loaded lazily
so importing this module never pulls torch — the heavy import happens on first
use. The **same** model must serve writes (B3) and reads (A4): the embedding
invariant (AD-4). Query embeddings get BGE's recommended retrieval instruction.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

_DEFAULT_MODEL = "BAAI/bge-base-en-v1.5"
_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class BgeEmbeddingProvider:
    """A local, free, asymmetric embedding backend."""

    def __init__(self, model_name: str = _DEFAULT_MODEL, *, device: str | None = None) -> None:
        self._model_name = model_name
        self._device = device
        self._model: SentenceTransformer | None = None

    def _ensure_model(self) -> SentenceTransformer:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # pragma: no cover - only without the embeddings extra
                raise RuntimeError(
                    "sentence-transformers is not installed; install the embeddings stack "
                    "(it is part of `pip install -e .[dev]`)."
                ) from exc
            self._model = SentenceTransformer(self._model_name, device=self._device)
        return self._model

    @property
    def dimension(self) -> int:
        dimension = self._ensure_model().get_embedding_dimension()
        if dimension is None:  # pragma: no cover - bge always reports a dimension
            raise RuntimeError("embedding model did not report a dimension")
        return dimension

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._ensure_model().encode(
            list(texts), normalize_embeddings=True, convert_to_numpy=True
        )
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        vector = self._ensure_model().encode(
            _QUERY_INSTRUCTION + text, normalize_embeddings=True, convert_to_numpy=True
        )
        return list(vector.tolist())
