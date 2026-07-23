# `adapters/knowledge/chroma_sqlite.py` — SQLite + Chroma store

**Layer:** adapters · **Stage:** 2 (+ Stage 6b moderation) · **Implements:** [`KnowledgeStore` + `Retriever`](../../domain/ports/knowledge.md) · **Pattern:** Repository

## 🎯 කාර්යය
KB port දෙකම implement කරන concrete store එක:
- **SQLite** (stdlib `sqlite3`) = structured facts + provenance වල **source of truth**.
- **ChromaDB** = chunk **vectors** (semantic search). bge vectors **අපිම explicitly supply කරනවා** — Chroma
  ගේ built-in embedding function එක පාවිච්චි කරන්නේ නෑ.

## 🔍 Code Walkthrough
- **`__init__`** — SQLite connect (`check_same_thread=False` + `threading.Lock` → thread-safe writes),
  FK pragma on, schema init; Chroma `PersistentClient` + cosine `kb_chunks` collection (telemetry off).
- **Catalog writes** — `add_service/variant/requirement/fee/office`, `link_service_office`,
  `add_district_variation`. හැම එකක්ම `_insert()` හරහා, `replace(entity, id=new_id)` return කරනවා.
- **Dedup + chunks** — `source_exists(url, content_hash)`, `upsert_source(...)`, `upsert_chunks(...)`:
  SQLite row එකක් දාලා `vector_ref = "chunk-{rowid}"` set කරලා, ඒ id එකෙන්ම Chroma එකට vector upsert.
- **`find_services`** ⭐ — **keyword-overlap ranking** (lexical). Query එකේ meaningful keywords (stopwords
  ඉවත් — "apply", "register" වගේ generic gov words + articles), service එකේ name/slug/description වල
  **whole-word** match ගණන අනුව score කරලා best matches return කරනවා. පරණ whole-query `LIKE` එකට වඩා
  natural-language phrasing වලට robust ("transfer my late father's land..." → hits).
- **Moderation (Stage 6b)** — `add_experience_report`, `list_sources_for_moderation` (auto_gathered/pending),
  `set_source_verification_status` (promote/reject), `delete_chunks_for_source` (reject → chunks +
  vectors delete, source row තියාගන්නවා dedup එකට).
- **`search`** (Retriever) — Chroma query → cosine distance **1.0 − distance = similarity**; provenance
  එක SQLite එකෙන් join කරලා `RetrievedChunk` හදනවා. `filters` → Chroma `where` (`$and`).

## 🔗 සම්බන්ධතා
- **Use කරන්නේ:** A2, A4, B3, seeder, moderation use case. Row↔entity mappers (`_row_to_*`) පහළින්.

## 💡 Design decisions
Raw `sqlite3` (ORM නෑ, user call). Chroma = pure vector store. `_NO_SERVICE = -1` sentinel (Chroma
metadata එකට `None` දාන්න බෑ). `find_services` lexical දැනට — vector service-matching A2/පසු stage එකකට.
