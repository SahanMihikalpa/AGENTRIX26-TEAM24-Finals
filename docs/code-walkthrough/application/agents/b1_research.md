# `application/agents/b1_research.py` — B1 · Research

**Layer:** application/agents · **Team 2 (Acquisition)** · **Stage:** 4b · [doc](../../../agents/b1-research.md) · **ADR:** AD-7

## 🎯 කාර්යය
A5 "GAP" කිව්වහම, නැති තොරතුරු **හොයාගෙන යන** පළමු step එක: **local source pool මුලින්ම** (reliable,
low-latency), pool එක මදි නම් විතරයි **live web** (`*.gov.lk` allow-list). Raw candidates `acquisition_buffer`
එකට ලියනවා (B2 ට).

## 🔍 Code Walkthrough
`ResearchAgent(source_pool, web_search=None, *, allowlist, max_results=5, min_local_results=1)`:
1. `source_pool.search(query)` → pool entries.
2. **Local-first:** pool results `< min_local_results` වුණොත් **විතරයි** web search (slower, allow-listed)
   කරනවා → buffer එකට extend.
3. Query එක `normalized_query` → `service_guess` → `user_query` (fallback order).
- Pool/web entries `{text, title, url, source_type, origin}` විදියට normalize (`origin`: "pool"/"web" —
  B2 confidence එකට වැදගත්).

## 🔗 සම්බන්ධතා
- **Uses:** [`SourcePool`](../../domain/ports/source_pool.md), [`WebSearch`](../../domain/ports/web_search.md).
- **Feeds:** B2 (via `acquisition_buffer`).

## 💡 Design decision
Pure **orchestrator** — fetch/parse ports (adapters) වල; `acquisition_loops` **supervisor** increment
කරනවා (මෙතන නෙවෙයි). Local-first = reliable demo + web = genuine novelty handling.
