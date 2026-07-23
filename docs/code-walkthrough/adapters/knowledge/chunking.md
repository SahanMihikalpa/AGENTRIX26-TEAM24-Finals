# `adapters/knowledge/chunking.py` — Text chunking + prose filter

**Layer:** adapters · **Stage:** 3/4 · **Pure** (stdlib only)

## 🎯 කාර්යය
Document text එකක් bge embedder එකට ගැලපෙන **overlapping chunks** වලට කැඩීම, සහ **garbage text filter**
එකක් — scanned-empty / form-field / legacy-font garbled text (English-only bge එකට pure noise) ඉවත් කරන්න.

## 🔍 Code Walkthrough
- **`chunk_text(text, *, max_chars=1000, overlap=120)`** — word-boundary windows. එක chunk එකක් `max_chars`
  ඉක්මවනවා නම් break කරලා, කලින් chunk එකේ **tail එකෙන් `overlap` chars** ඊළඟ chunk එකට carry කරනවා
  (retrieval continuity). Deterministic; blank input → `[]`.
- **`looks_like_prose(text, ...)`** — heuristic 3ක්: (1) minimum length, (2) **ASCII ratio** ≥ 0.80
  (non-ASCII gibberish reject — bge-en එකට හරි), (3) **word ratio** ≥ 0.5 (tokens වලින් වැඩිය "words"
  (`[A-Za-z]{2,}`) විය යුතුයි — form/garble text reject).
- `_overlap_tail(...)` — chunk එකක tail words `overlap_chars` ට ගන්නවා.

## 🔗 සම්බන්ධතා
- **Use කරන්නේ:** seed `build` CLI ([`cli/build_catalog`](../../cli/build_catalog.md)); B3 එකටත් අනාගතේ
  shared chunking විදියට available.

## 💡 Design decision
ASCII ratio + word ratio = **චීප, dependency-free garble discriminator**. Legacy-font Sinhala/Tamil
(form PDFs වලින්) punctuation gibberish විදියට extract වෙනවා — මේ filter එකෙන් KB එකට noise වදින්නේ නෑ.
