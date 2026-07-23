# `infrastructure/cache.py` — Query→answer cache

**Layer:** infrastructure · **Stage:** 3 · **ADR:** AD-12

## 🎯 කාර්යය
එකම `service + variant + district` query එකකට (සහ demo re-runs වලට) **මුළු agent graph එකම skip කරලා**,
කලින් හදපු `ActionPack` එක ආපහු දෙනවා — scarce LLM quota එක save කරන්න.

## 🔍 Code Walkthrough
- `CacheKey` (frozen dataclass) — `service_id`, `variant_id?`, `district?`. `CacheKey.build(...)` එකෙන්
  district එක **normalize** කරනවා (strip + lowercase) → "Colombo" සහ "  colombo " එකම key එකක්.
- `AnswerCache` — thread-safe **LRU** cache:
  - `get(key)` / `put(key, pack)` — `OrderedDict` + lock; `maxsize` (default 256) ඉක්මවුවොත් least-recently-used
    එක evict වෙනවා.
  - `invalidate_service(service_id)` — ඒ service එකේ **හැම cached answer එකක්ම** අයින් කරනවා.
    B3 KB එකට අලුත් දෙයක් ලියද්දී මේක call කරනවා → stale answer serve වෙන්නේ නෑ (AD-12 trade-off එක neutralize).

## 🔗 සම්බන්ධතා
- **Use කරන්නේ:** API/graph layer එක (chat request එකකදී cache hit බලනවා; A6 answer එකක් හදාපු පස්සේ `put`).
- Store කරන්නේ domain `ActionPack` එකම (serialize කරන්නේ නෑ — in-memory).

## 💡 Design decision — ඇයි in-memory (SQLite නෙවෙයි)?
`docs/04` "SQLite table" කිව්වත්, දැනට **in-memory LRU** එකක්. ඒකෙන් AD-12 ගේ මූලික අරමුණ (එකම process
එකේ demo re-runs skip කරන එක) සම්පූර්ණයෙන් ඉටු වෙනවා, nested `ActionPack` එක SQLite එකට serialize කරන
වියදම නැතුව. Cross-restart persistence එක Stage 6 DTOs එනකම් කල් දාලා (delta එක `docs/10` එකේ).
