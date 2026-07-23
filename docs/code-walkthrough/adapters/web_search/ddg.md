# `adapters/web_search/ddg.py` — DuckDuckGo search (keyless fallback)

**Layer:** adapters · **Stage:** 3 · **Implements:** [`WebSearch`](../../domain/ports/web_search.md)

## 🎯 කාර්යය
**Keyless fallback** web search එක (`ddgs` package) — Tavily key එකක් නැති වුණත් research වැඩ කරනවා.

## 🔍 Code Walkthrough
- `DdgWebSearch(*, client=None)` — SDK lazy-import; client inject කරන්න පුළුවන්.
- `search(query, *, allowlist, max_results=5)`:
  1. DuckDuckGo එකට server-side domain filter නෑ → query එකට **`site:` operators** එකතු කරනවා
     (`_scoped_query`, allow-list domains) → gov.lk bias.
  2. **Over-fetch** (`max_results × 5`) → හැම URL එකකම `host_allowed` filter → `max_results` දක්වා cap.
  3. Result keys defensively read (`href`/`url`, `body`/`snippet`).

## 🔗 සම්බන්ධතා
- **Use කරන්නේ:** [`b1_research.py`](../../application/agents/b1_research.md) (Tavily නැත්නම්/fallback).

## 💡 Design decision
DDG එකට domain filter නෑ නිසා: `site:` bias + over-fetch + local filter. Non-gov results ගොඩක් එනවා
නිසා ×5 over-fetch. Live smoke test එක opt-in (`RUN_LIVE_TESTS=1`), network එක ඕන නිසා.
