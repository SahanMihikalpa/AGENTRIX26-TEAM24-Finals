"""Real bge embedding test — skipped automatically if sentence-transformers is absent.

When run, the first call downloads the ~440 MB model to the HuggingFace cache.
"""

from __future__ import annotations

import pytest

pytest.importorskip("sentence_transformers")

from app.adapters.embeddings.bge import BgeEmbeddingProvider

_BGE_DIM = 768


def test_bge_dimension_and_embeddings() -> None:
    provider = BgeEmbeddingProvider()
    assert provider.dimension == _BGE_DIM

    query_vector = provider.embed_query("how do I renew my NIC?")
    assert len(query_vector) == _BGE_DIM

    doc_vectors = provider.embed_documents(["first passage", "second passage"])
    assert len(doc_vectors) == 2
    assert all(len(vector) == _BGE_DIM for vector in doc_vectors)
