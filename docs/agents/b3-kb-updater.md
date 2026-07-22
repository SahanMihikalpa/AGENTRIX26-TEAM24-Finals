# B3 · KB-Updater

**Team:** Knowledge Acquisition · **Type:** Embed + upsert (writer)

## Issue it solves
Curated records are useless until they're **in the knowledge base** and retrievable — this is the
step that actually makes the RAG **self-expanding**, and the cache that makes the first user's
research benefit everyone after.

## Single responsibility
Persist curated records into SQLite + ChromaDB (chunk → embed → upsert), with dedup and flags.

## Inputs → Outputs
- **Input:** curated records + `SOURCE` from B2.
- **Output:** committed rows (SQLite) + vectors (Chroma); returns control to A4 for re-retrieval.

## Step logic
1. **Dedup** against existing `SOURCE`/records (by url + content hash).
2. Insert structured rows into SQLite.
3. Chunk text, **embed locally**, upsert into ChromaDB with metadata
   (`service_id`, `district`, `source_id`, `verification_status`).
4. Link `KB_CHUNK.vector_ref` ↔ structured rows; signal "KB updated".

## Decisions & technologies
- **Decision:** **idempotent upsert** with content-hash dedup; merge policy = never let
  `auto_gathered` overwrite `verified`.
- **Tech:** SQLite + ChromaDB upsert + local `bge-base-en-v1.5` embeddings.

## Alternatives
| Alternative | Why not |
|---|---|
| Append without dedup | KB bloats and double-counts on repeated gaps. |
| Rebuild the whole index each time | Wasteful; slow; unnecessary for incremental writes. |

## Why optimal
Incremental, idempotent, provenance-tagged writes are exactly what a **lazily-growing, cached**
knowledge base needs — fast, safe, and cheap (local embeddings).

## Guardrails
Dedup prevents duplicates; `verification_status` preserved; the loop cap (`N`) bounds how often this
runs per query.

## State touched
Writes to the KB; sets a "kb_updated" flag so the supervisor re-runs A4.
