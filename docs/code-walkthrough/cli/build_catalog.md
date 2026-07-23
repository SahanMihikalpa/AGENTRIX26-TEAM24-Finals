# `cli/build_catalog.py` — `build` command (raw docs → catalog skeleton)

**Layer:** cli · **Stage:** 4 · **Run:** `python -m app.cli build`

## 🎯 කාර්යය
Raw seed documents → `catalog.json` **skeleton** එකක් හැදීම. `--raw-dir` එකේ හැම sub-directory එකක්ම එක
**service** (folder name = slug); ඇතුළේ readable document එකක් `SOURCE` එකක්, clean text එක `chunks[]`
වලට chunk වෙනවා.

## 🔍 Code Walkthrough
`build_catalog_skeleton(raw_dir, parser, ...)`:
- හැම service folder එකකටම files process කරනවා: `_parse_file` (PDF/HTML/txt), `< _MIN_DOC_CHARS` (120) →
  **skipped-empty** (scanned PDF); `chunk_text` → chunks; **`looks_like_prose`** නැති chunks **drop**
  (garble filter).
- Source entry `verified` + `confidence=1.0` (authored seed); structured facts (**variants/requirements/
  fees/offices**) **empty stubs** විදියට — human curation එකට.
- `BuildReport` (per-file outcomes) + `_print_report` (හොඳ terminal report).

## 🔗 සම්බන්ධතා
[chunking](../adapters/knowledge/chunking.md) (`chunk_text` + `looks_like_prose`),
[parser](../adapters/parser/pymupdf.md). Output → human curation → [`seed`](seed.md).

## 💡 Design decision — provenance mechanise, facts human-curate
මේ tool එක **provenance + chunking විතරයි** කරනවා — රජයේ facts කවදාවත් **invent කරන්නේ නෑ**. Stubs
(category + variants/fees…) මිනිසෙක් fill කරනවා → accuracy (QA-1). Garble filter නිසා bge-en එකට clean
English text විතරයි යනවා.
