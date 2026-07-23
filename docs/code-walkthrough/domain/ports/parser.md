# `domain/ports/parser.py` — `SourceParser` port

**Layer:** domain/ports · **Stage:** 1 · **Used by:** B1 Research

## 🎯 කාර්යය
Raw bytes/HTML → **පිරිසිදු text + metadata** කරන socket එක. B1 fetch කරන PDF/pages, B2 curate කරන්න කලින්
මෙතනින් clean වෙනවා.

## 🔍 Code Walkthrough
- `ParsedDocument` (frozen dataclass) — `text`, `source_type`, `title?`, `url?`, `published_date?`,
  `metadata` (dict).
- `SourceParser.parse_pdf(data: bytes, *, url=None) -> ParsedDocument`
- `SourceParser.parse_html(html: str, *, url=None) -> ParsedDocument`

## 🔗 සම්බන්ධතා
- **Implement කරන්නේ:** [`adapters/parser/pymupdf.py`](../../adapters/parser/pymupdf.md)
  (PDF = PyMuPDF, HTML = trafilatura).
- **Use කරන්නේ:** B1 (web/pool documents parse කරන්න), source_pool adapter.

## 💡 Design decision
`source_type` එක parser එකෙන් **provisional hint** එකක් විතරයි (PDF→circular, HTML→portal); හරි category
එක B2 curate කරද්දී set කරනවා — parser එක bytes බලලා gov-document class එකක් **අනුමාන කරන්නේ නෑ**.
