# `domain/ports/knowledge.py` — `KnowledgeStore` + `Retriever` ports

**Layer:** domain/ports · **Stage:** 1 (+ Stage 6b moderation methods) · **Pattern:** Repository

## 🎯 කාර්යය
Knowledge Base (KB) එකට **socket දෙකක්**. දෙකම implement කරන්නේ එකම adapter එකෙන්
([`chroma_sqlite.py`](../../adapters/knowledge/chroma_sqlite.md)), ඒත් වෙන් කරලා තියෙන්නේ එක එක agent එකේ
dependency එක පටු (narrow) කරගන්න.

## 🔍 Code Walkthrough

**`KnowledgeStore`** — structured facts + provenance (source of truth):
- *Catalog writes* (seeding / B3): `add_service`, `add_variant`, `add_requirement`, `add_fee`,
  `add_office`, `link_service_office`, `add_district_variation`.
- *Provenance + dedup* (B3): `source_exists(url, content_hash)`, `upsert_source(...)`,
  `upsert_chunks(chunks, embeddings)` — SQLite rows + Chroma vectors එකට save කරනවා (index එකෙන් zip).
- *Catalog reads* (A2/A4): `find_services` (lexical), `get_service`, `list_variants`, `get_requirements`,
  `get_fees`, `get_offices(..., district=None)`.
- *Moderation (Stage 6b):* `add_experience_report`, `list_sources_for_moderation`,
  `set_source_verification_status` (promote/reject), `delete_chunks_for_source` (reject quarantine —
  chunks අයින් කරනවා, ඒත් `source` row එක dedup එකට තියාගන්නවා).

**`Retriever`** — `search(query_embedding, *, filters=None, top_k=5) -> list[RetrievedChunk]`. Semantic
vector search + provenance + scores.

## 🔗 සම්බන්ධතා
- **Implement කරන්නේ:** [`adapters/knowledge/chroma_sqlite.py`](../../adapters/knowledge/chroma_sqlite.md).
- **Use කරන්නේ:** A2 (find_services), A4 (search + get_*), B3 (upsert), seeder, moderation use case.

## 💡 Design decision
Reads-by-key (`KnowledgeStore`) සහ semantic-search (`Retriever`) වෙන් කිරීම = Interface Segregation.
A4 වගේ agent එකකට ports දෙකම inject කරනවා; simple agent එකකට එකක් විතරයි.
