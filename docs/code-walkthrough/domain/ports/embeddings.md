# `domain/ports/embeddings.py` — `EmbeddingProvider` port

**Layer:** domain/ports · **Stage:** 1 · **ADR:** AD-4

## 🎯 කාර්යය
Text එකක් → **vector** එකක් කරන socket එක (semantic search එකට). Local, free embeddings වලට interface එක.

## 🔍 Code Walkthrough
- `dimension` (property) → vector එකේ ප්‍රමාණය (vector store එකට match වෙන්න ඕන).
- `embed_documents(texts) -> list[list[float]]` — save කරන්න passages embed කරනවා (B3).
- `embed_query(text) -> list[float]` — retrieve කරන්න query එකක් embed කරනවා (A4).

**Query සහ document වෙනම** තියෙන්නේ ඇයි? BGE වගේ **asymmetric** models query එකට වෙනම instruction එකක්
prepend කරනවා.

## 🔗 සම්බන්ධතා
- **Implement කරන්නේ:** [`adapters/embeddings/bge.py`](../../adapters/embeddings/bge.md) (local `bge-base-en-v1.5`).
- **Use කරන්නේ:** A4 (read), B3/seeder (write), chroma store.

## 💡 Design decision — Embedding invariant (AD-4)
**Write එකේ (B3) සහ read එකේ (A4) එකම model එක** පාවිච්චි කරන්නම ඕන — model දෙකක් mix කළොත් retrieval
එක නිහඬව නරක් වෙනවා.
