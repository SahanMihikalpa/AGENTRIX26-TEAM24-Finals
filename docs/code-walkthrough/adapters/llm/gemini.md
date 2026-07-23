# `adapters/llm/gemini.py` — Gemini provider (primary)

**Layer:** adapters · **Stage:** 3 · **Extends:** [`LangChainLLMProvider`](base.md) · **ADR:** AD-6

## 🎯 කාර්යය
**Primary LLM** එක — Google Gemini Flash (`langchain_google_genai.ChatGoogleGenerativeAI` wrap කරනවා).

## 🔍 Code Walkthrough
- `GeminiLLMProvider(api_key, *, model="gemini-2.5-flash")` — `base.py` ට factory එකක් දෙනවා.
- **Lazy import:** provider SDK එක import වෙන්නේ factory එක ඇතුළේ (first use) — module import safe.
- API key එක `pydantic.SecretStr` වලින් wrap කරනවා (provider ගේ typed field එක).

## ⚠️ වැදගත් — model එක `gemini-2.5-flash`
`gemini-2.0-flash` මේ project ගේ key එකට free-tier `limit: 0` (429 RESOURCE_EXHAUSTED). `gemini-2.5-flash`
(සහ `-lite`) වැඩ කරනවා — ඒ නිසා default එක 2.5. Live smoke test එකෙන් verify කරලා. Gemini throttle වුණොත්
[gateway](../../infrastructure/llm_gateway.md) එක Groq එකට fallback.

## 🔗 සම්බන්ධතා
Wire වෙන්නේ [`api/runtime.py`](../../api/runtime.md) එකේ (settings key + model). Fallback pair:
[`groq.py`](groq.md).
