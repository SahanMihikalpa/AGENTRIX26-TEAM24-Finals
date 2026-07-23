# `domain/ports/source_pool.py` — `SourcePool` port

**Layer:** domain/ports · **Stage:** 1 (adapter Stage 3) · **ADR:** AD-7 (local-first)

## 🎯 කාර්යය
**Local source pool** එකට read access එක — කලින් එකතු කරගත්ත gazettes/circulars/portal PDFs ගොඩ. B1
Research මුලින්ම **මේ pool එකේ** හොයනවා (live web එකට කලින්), ඒකෙන් reliable + වේගවත් demo එකක්.

## 🔍 Code Walkthrough
- `PooledDocument` (frozen dataclass) — pool එකේ **තවම KB එකට ingest කරලා නැති** document එකක්:
  `text`, `title`, `source_type`, `url?`, `published_date?`.
- `SourcePool.search(query, *, limit=5) -> list[PooledDocument]`.

## 🔗 සම්බන්ධතා
- **Implement කරන්නේ:** [`adapters/source_pool/filesystem.py`](../../adapters/source_pool/filesystem.md)
  (`data/source_pool/` යටතේ files කියවලා parse කරනවා).
- **Use කරන්නේ:** [`b1_research.py`](../../application/agents/b1_research.md).

## 💡 Design decision
Pool එක KB එකෙන් **වෙනම store** එකක් — pool docs තවම ingest වෙලා නෑ. B1 surface කරනවා → B2 curate →
B3 KB එකට ලියනවා. (C4-L3, [`docs/02`](../../02-architecture.md).)
