# `adapters/llm/groq.py` — Groq provider (fallback)

**Layer:** adapters · **Stage:** 3 · **Extends:** [`LangChainLLMProvider`](base.md) · **ADR:** AD-6

## 🎯 කාර්යය
**Fallback LLM** එක — Groq-hosted Llama (`langchain_groq.ChatGroq`). Gemini fail/throttle වුණොත් gateway
එක මේකට මාරු වෙනවා.

## 🔍 Code Walkthrough
- `GroqLLMProvider(api_key, *, model="llama-3.1-8b-instant")` — `gemini.py` ට සමාන thin subclass.
- Lazy import, `SecretStr(api_key)`. Interface එක සම්පූර්ණයෙන්ම gemini එකට සමානයි (එකම port).

## 🔗 සම්බන්ධතා
- **Wrap කරන්නේ:** [`llm_gateway.py`](../../infrastructure/llm_gateway.md) (`fallback=` argument).
- Live smoke test එකෙන් verify — Groq calls **pass** වෙනවා (working key).

## 💡 Design decision
Gemini/Groq එකම `LangChainLLMProvider` base එකෙන් — provider swap කරන එක trivial. Groq = free-tier,
native tool-calling, ඉතා වේගවත් (Gemini quota outage එකකදී safety net).
