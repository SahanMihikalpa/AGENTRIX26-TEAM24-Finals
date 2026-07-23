# `domain/ports/web_search.py` — `WebSearch` port

**Layer:** domain/ports · **Stage:** 1 · **ADR:** AD-7 · **Driver:** QA-7 (allow-list)

## 🎯 කාර්යය
Live web එකෙන් හොයන socket එක (B1 ගේ fallback path එක — KB එකේ නැති නම් විතරයි).

## 🔍 Code Walkthrough
- `WebResult` (frozen dataclass) — එක web hit එකක්: `title`, `url`, `snippet`.
- `WebSearch.search(query, *, allowlist, max_results=5) -> list[WebResult]` — **allow-list එකේ host තියෙන
  results විතරයි** return කරනවා.

## 🔗 සම්බන්ධතා
- **Implement කරන්නේ:** [`adapters/web_search/tavily.py`](../../adapters/web_search/tavily.md) (primary),
  [`ddg.py`](../../adapters/web_search/ddg.md) (keyless fallback). Allow-list logic:
  [`allowlist.py`](../../adapters/web_search/allowlist.md).
- **Use කරන්නේ:** [`b1_research.py`](../../application/agents/b1_research.md).

## 💡 Design decision — QA-7 allow-list
`allowlist` එක **argument එකක්** විදියට port එකේ තියෙනවා, ඒත් **enforcement එක adapter එකේ** — කිසිම agent
එකකට වැරදිලාවත් `*.gov.lk` වලින් පිට යන්න බෑ.
