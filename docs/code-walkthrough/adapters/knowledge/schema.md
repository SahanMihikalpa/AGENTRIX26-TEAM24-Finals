# `adapters/knowledge/schema.sql` — SQLite schema (ER)

**Layer:** adapters · **Stage:** 2 · **Mirrors:** [`docs/05` ER diagram](../../../05-data-model.md)

## 🎯 කාර්යය
Structured facts + provenance වලට **source of truth** එක වන SQLite tables. `CREATE TABLE IF NOT EXISTS`
නිසා store එක boot වෙද්දී idempotent-ව හැදෙනවා.

## 🔍 Tables
- **`source`** — හැම fact එකකම මූලාශ්‍රය: `confidence`, `verification_status`, + `content_hash`
  (B3 dedup එකට — ER එකේ නෑ).
- **Catalog:** `service` → `service_variant` → `requirement` / `fee`. `office` + `service_office`
  (many-to-many link), `district_variation`.
- **`kb_chunk`** — vector retrieval එකට text chunks (`vector_ref` = Chroma id, `service_id` nullable).
- **`experience_report`**, **`session`**, **`session_message`**, **`checklist`** (`payload_json`).
- **Indexes:** variant→service, requirement/fee→variant, chunk→source, source url + hash (dedup lookups).

## 💡 Design decisions (deltas from ER)
- **Money = `TEXT`** (`amount_lkr`) — `Decimal` precision රැකගන්න (`REAL` float නෙවෙයි).
- **Dates = ISO strings** (`TEXT`); enums store කරන්නේ **value** එකෙන්.
- `ON DELETE CASCADE` — service එකක් delete කළොත් ඒකෙ variants/chunks ආදිය auto delete.
- `content_hash` column එක ER එකේ නෑ — B3 dedup එකට එකතු කරලා.

## 🔗 සම්බන්ධතා
[`chroma_sqlite.py`](chroma_sqlite.md) `_init_schema()` එකෙන් මේ file එක `executescript` කරනවා.
