# `adapters/embeddings/bge.py` — Local BGE embeddings

**Layer:** adapters · **Stage:** 2 · **Implements:** [`EmbeddingProvider`](../../domain/ports/embeddings.md) · **ADR:** AD-4

## 🎯 කාර්යය
Text → vector කරන්න **local, free** model එකක් (`BAAI/bge-base-en-v1.5`, sentence-transformers). API එකක්
නෑ → rate-limit නෑ, offline, free — Gemini quota එක reasoning එකට reserve වෙනවා.

## 🔍 Code Walkthrough
- **Lazy loading:** `_ensure_model()` — model එක load වෙන්නේ **පළමු use එකේදී** විතරයි. ඒ නිසා මේ module
  එක import කරද්දී torch load වෙන්නේ නෑ (import fast). torch නැත්නම් clear `RuntimeError`.
- `dimension` → 768 (vector store එකට match වෙන්න ඕන).
- `embed_documents(texts)` → normalize කරපු vectors (save/write path, B3).
- `embed_query(text)` → **BGE query instruction එක prepend කරලා** ("Represent this sentence for
  searching relevant passages: ") normalize කරනවා (read path, A4).

## 🔗 සම්බන්ධතා
- **Use කරන්නේ:** A4 (embed_query), B3 + seeder (embed_documents), chroma store.

## 💡 Design decision — Asymmetric + AD-4 invariant
Query එකට වෙනම instruction එකක් (asymmetric model). **Write + read එකේ එකම model එක** පාවිච්චි කරන්නම
ඕන — නැත්නම් retrieval නිහඬව නරක් වෙනවා. Tests වලදී torch-free `DeterministicEmbedder` එකක් පාවිච්චි කරලා
fast තියාගන්නවා; real bge test එක එක පාරයි model එක download කරනවා.
