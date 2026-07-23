# `adapters/web_search/tavily.py` — Tavily web search (primary)

**Layer:** adapters · **Stage:** 3 · **Implements:** [`WebSearch`](../../domain/ports/web_search.md) · **ADR:** AD-7

## 🎯 කාර්යය
**Primary web search** එක — Tavily API (free tier). B1 ගේ live-web fallback path එකේ මුල් choice එක.

## 🔍 Code Walkthrough
- `TavilyWebSearch(api_key, *, client=None)` — SDK lazy-import; `client` inject කරන්න පුළුවන් (test/DI).
- `search(query, *, allowlist, max_results=5)`:
  1. Tavily `include_domains` (server-side allow-list) + `search_depth="basic"`.
  2. හැම result URL එකකම **`host_allowed` local check** (defense in depth — server-side + local).
  3. `WebResult(title, url, snippet=content)` map.

## 🔗 සම්බන්ධතා
- **Use කරන්නේ:** [`b1_research.py`](../../application/agents/b1_research.md). Fallback pair:
  [`ddg.py`](ddg.md). Allow-list: [`allowlist.py`](allowlist.md).

## 💡 Design decision
Allow-list **දෙපාරක්** apply (server `include_domains` + local `host_allowed`) — off-allowlist result
එකක් වත් slip වෙන්නේ නෑ. Live smoke test එකෙන් Tavily calls **pass** වෙනවා.
