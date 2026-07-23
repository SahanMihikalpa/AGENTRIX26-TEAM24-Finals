# `adapters/parser/pymupdf.py` — PDF + HTML parser

**Layer:** adapters · **Stage:** 3 · **Implements:** [`SourceParser`](../../domain/ports/parser.md)

## 🎯 කාර්යය
Raw bytes/HTML → clean text + provenance:
- **PDF** → PyMuPDF (`pymupdf`): හැම page එකකම text join + document metadata.
- **HTML** → trafilatura: main-article text (nav/boilerplate strip) + metadata.

## 🔍 Code Walkthrough
- `parse_pdf(data, *, url=None)` — `pymupdf.open(stream=data)` → pages loop → text; `document.metadata`
  එකෙන් title/author/creationDate. `source_type = CIRCULAR` (provisional).
- `parse_html(html, *, url=None)` — `trafilatura.extract(...)` (favor_recall) + `extract_metadata`
  (best-effort, try/except). `source_type = PORTAL` (provisional).
- Both **lazy-import** (module import → PyMuPDF/trafilatura pull වෙන්නේ නෑ).
- Date helpers: `_parse_pdf_date` (`D:YYYYMMDD...`), `_parse_iso_date`.

## ⚠️ Typing note
PyMuPDF `py.typed` ship කරනවා ඒත් `Document` API එක partially typed — ඒ නිසා PDF handle එක `Any` +
එක localized `# type: ignore[no-untyped-call]` එකකින් document කරලා.

## 💡 Design decision — provisional `source_type`
Parser එක bytes බලලා gazette/circular class එකක් **අනුමාන කරන්නේ නෑ** — medium-based hint එකක් විතරයි
(PDF→circular, HTML→portal). B2 curate කරද්දී authoritative type එක set කරනවා.

## 🔗 සම්බන්ධතා
Use කරන්නේ B1 (web docs) + [`source_pool/filesystem.py`](../source_pool/filesystem.md) (pool files).
