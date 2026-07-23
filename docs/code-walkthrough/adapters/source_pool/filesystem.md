# `adapters/source_pool/filesystem.py` — Local source-pool adapter

**Layer:** adapters · **Stage:** 3 · **Implements:** [`SourcePool`](../../domain/ports/source_pool.md) · **ADR:** AD-7

## 🎯 කාර්යය
`data/source_pool/` directory එකේ තියෙන pre-collected files (PDF/HTML/txt) කියවලා, query එකට **lexical
match** වෙන best `PooledDocument`s return කිරීම. B1 මුලින්ම මේකෙන් හොයනවා (web එකට කලින්).

## 🔍 Code Walkthrough
- `FilesystemSourcePool(root, *, parser=None)` — pool directory + optional `SourceParser`.
- `search(query, *, limit=5)`:
  1. directory එකේ හැම file එකක්ම load (`_load`).
  2. `_score` — query terms සහ **filename terms** (weight ×2) + **body terms** overlap ගණන.
  3. score desc + name stable sort → top `limit`.
- `_load(path)` — suffix අනුව: `.txt/.md` → plain read; `.pdf` → `parser.parse_pdf`; `.html/.htm` →
  `parser.parse_html`. Parser නැත්නම් PDF/HTML skip.

## 💡 Design decision — lexical (vector නෙවෙයි)
MVP එකට matching **lexical** (filename + content terms) — fast, dependency-light, staged demo sources
වලට ඇති. Doc එකේ "ChromaDB over the pool" vector index එක noted enhancement එකක්. Parsing එක
`SourceParser` එකට delegate — මේ adapter එක thin file→`PooledDocument` mapper එකක් විතරයි.

## 🔗 සම්බන්ධතා
- **Use කරන්නේ:** [`b1_research.py`](../../application/agents/b1_research.md). Parser:
  [`pymupdf.py`](../parser/pymupdf.md).
