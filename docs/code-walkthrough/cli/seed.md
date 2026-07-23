# `cli/seed.py` — `seed` command (catalog.json → KB)

**Layer:** cli · **Stage:** 2 · **Run:** `python -m app.cli seed`

## 🎯 කාර්යය
`catalog.json` එකක් SQLite + Chroma එකට load කිරීම (knowledge ports හරහා). Load කරන්න කලින්
**validate** කරනවා.

## 🔍 Code Walkthrough
`run(args)`:
1. catalog file එක read + **`validate_catalog`** (referential integrity, enums, category, Decimal fees).
   problems තිබුණොත් print කරලා exit 1.
2. **`--dry-run`** → validate විතරයි (torch load නෑ, DB write නෑ) → hand-authored catalog check කරන්න හොඳයි.
3. එහෙම නැත්නම්: `ChromaSqliteStore` + `BgeEmbeddingProvider` හදලා `KnowledgeSeeder.load(data)` → stats print.
- Paths default = `Settings` (backend/ එකෙන් run කරන්න).

## 🔗 සම්බන්ධතා
[`KnowledgeSeeder`](../adapters/knowledge/seed.md), [`ChromaSqliteStore`](../adapters/knowledge/chroma_sqlite.md),
[`BgeEmbeddingProvider`](../adapters/embeddings/bge.md).

## 💡 Design decision
`--dry-run` = torch-free validation → CI/authoring වලට fast feedback. Ports හරහා → store swap කරන්න පුළුවන්.
