# `adapters/knowledge/seed.py` — Catalog JSON → KB loader

**Layer:** adapters · **Stage:** 2 · **Depends on:** [`KnowledgeStore`](../../domain/ports/knowledge.md) + [`EmbeddingProvider`](../../domain/ports/embeddings.md) (ports විතරයි)

## 🎯 කාර්යය
Catalog JSON file එකක් (services + variants + requirements + fees + offices + chunks) → KB එකට load
කිරීම (structured rows **+** vectors). Ports විතරයි use කරන නිසා real store එකට හෝ fake එකට run කරන්න පුළුවන්.

## 🔍 Code Walkthrough
- **`validate_catalog(data, *, check_category=True)`** — JSON එකේ ගැටලු human-readable list එකක් විදියට
  return කරනවා (empty = valid). Checks: **referential integrity** (හැම `source_key` එකක්ම declared source
  එකකට resolve වෙනවද), **enum membership** (`source_type`/`verification_status`/`office_type`), **Decimal**
  parse-able fees, required fields. `check_category` on වුණොත් `ServiceCategory` vocabulary එකත් enforce
  (CLI/authored data වලට); `KnowledgeSeeder.load` එකේදී **off** — programmatic/auto-gathered data වලට
  free-form category (B3 mirror).
- **`SeedStats`** — insert කරපු ගණන් (sources, services, variants, …).
- **`KnowledgeSeeder`** — `load_from_json(path)` / `load(data)`:
  1. validate (fail → `ValueError`).
  2. sources upsert (key → Source map).
  3. හැම service එකකටම: service → variants → requirements/fees, offices (+ link), district_variations,
     chunks (pending එකතු කරලා අන්තිමට **batch embed + upsert_chunks** — එක embed call එකයි).
- Helpers: `_require_id` (store id දුන්නද verify), `_parse_date`.

## 🔗 සම්බන්ධතා
- **Use කරන්නේ:** [`cli/seed.py`](../../cli/seed.md). JSON contract: `data/seed/catalog.example.json`.

## 💡 Design decision
Chunks **batch embed** (loop එකේ එකින් එක නෙවෙයි) → embedder call එකයි. Validation strict (referential
integrity) නිසා broken catalog එකක් KB එකට වදින්නේ නෑ.
