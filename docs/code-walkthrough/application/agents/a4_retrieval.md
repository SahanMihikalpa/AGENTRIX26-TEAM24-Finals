# `application/agents/a4_retrieval.py` — A4 · Retrieval (RAG)

**Layer:** application/agents · **Team 1** · **Stage:** 4 · [doc](../../../agents/a4-retrieval.md)

## 🎯 කාර්යය
Resolved case එකට **grounding evidence** ගැනීම — query එක local embed කරලා (AD-4), ChromaDB එකෙන්
top-k chunks (service_id filter එක්ක) vector-search කරනවා.

## 🔍 Code Walkthrough
`RetrievalAgent(embedder, retriever, *, top_k=5)` — `__call__`:
1. `embedder.embed_query(normalized_query)`.
2. `service_id` තිබුණොත් `filters={"service_id": ...}`.
3. `retriever.search(embedding, filters, top_k)` → `RetrievedChunk`s → `retrieved_to_state(...)` map.

Scores **honestly** report කරනවා (inflate නෑ) → A5 ට real gaps detect කරන්න පුළුවන්.

## 🔗 සම්බන්ධතා
- **Uses:** [`EmbeddingProvider`](../../domain/ports/embeddings.md), [`Retriever`](../../domain/ports/knowledge.md),
  [`serialization.retrieved_to_state`](../graph/serialization.md).
- **Feeds:** A5 (grade), A6 (citations).

## 💡 Design decision — Leanness (AD-3)
`retrieved` එකට **chunk text + provenance විතරයි** දානවා (A5 grade කරන්න ඕන දේ). Exact structured rows
(REQUIREMENT/FEE/OFFICE) A6 **generation time එකේදී store එකෙන් කෙළින්ම කියවනවා** → checkpointed state එක
bloat වෙන්නේ නෑ, **සහ** gap-loop එකෙන් add වුණ fresh rows A6 ට හැමවිටම පේනවා.
