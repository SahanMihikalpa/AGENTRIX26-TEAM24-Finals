# `infrastructure/llm_gateway.py` — Rate-limited LLM gateway

**Layer:** infrastructure · **Stage:** 3 · **ADR:** AD-10 · **Pattern:** Decorator + Façade

## 🎯 කාර්යය
හැම agent එකක්ම Gemini/Groq එකට කතා කරන්නේ **මේ එකම choke-point එක හරහා** — free-tier ceiling එක යටින්
තියාගන්න. මේක `LLMProvider` port එකේම **decorator** එකක්: මේකත් `LLMProvider` එකක්, ඒ නිසා agents දන්නෙත්
නෑ gateway එකක් ඉන්නවා කියලා.

## 🔍 Code Walkthrough

**`TokenBucket`** — thread-safe rate limiter:
- `rate_per_minute` (default 15) → `refill_per_sec = rpm/60`. `acquire()` කරද්දී tokens නැත්නම්
  **block වෙනවා** (sleep) tokens refill වෙනකම්.
- Clock + sleep **inject කරන්න පුළුවන්** → real time නැතුව deterministic-ව test කරන්න පුළුවන්.

**`LLMGateway`** — වගකීම් 3ක්, පිළිවෙළට:
1. **Throttle** — හැම call එකකට කලින් `bucket.acquire()`.
2. **Retry** — fail වුණොත් exponential backoff (`0.5 × 2^attempt`) එක්ක `max_retries` වාරයක් retry.
3. **Fallback** — primary (Gemini) එක retry ඔක්කොම fail නම් → secondary (Groq) එකට මාරු වෙලා ආයෙත් try.

`_run()` (primary → fallback) සහ `_attempt()` (rate-limit + retry loop) — internal helpers. Generic
`R` TypeVar නිසා `complete` (→str) සහ `complete_structured` (→T) දෙකටම එකම logic එක.

## 🔗 සම්බන්ධතා
- **Wrap කරන්නේ:** [`GeminiLLMProvider`](../adapters/llm/gemini.md) (primary) +
  [`GroqLLMProvider`](../adapters/llm/groq.md) (fallback).
- **Use කරන්නේ:** හැම LLM agent එකක්ම (gateway එක port එක විදියට inject වෙනවා —
  [`api/runtime.py`](../api/runtime.md) එකේ wire වෙනවා).

## 💡 Design decision — ඇයි "any exception" retry කරන්නේ?
Provider-specific error types (`google.genai.errors...`) import කළොත් adapter detail එකක් infrastructure
එකට කාන්දු වෙනවා. ඒ නිසා **ඕනම exception එකක් retry කරනවා**, `max_retries` වලින් bound කරලා — hexagonal
boundary එක පිරිසිදුව තියාගන්න ගත්ත deliberate trade-off එකක්. (Gemini 429 → Groq fallback එක මේකෙන්
automatically වැඩ කරනවා.)
