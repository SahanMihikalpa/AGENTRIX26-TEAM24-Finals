# `domain/ports/llm.py` — `LLMProvider` port

**Layer:** domain/ports · **Stage:** 1 · **Pattern:** Strategy / Adapter · **ADR:** AD-6

## 🎯 කාර්යය
LLM එකකින් "reasoning" ගන්න **socket (interface)** එක. මේක `Protocol` එකක් — method දෙකක් define කරනවා,
implementation එකක් නෑ. Agents මේ **port එකට** කතා කරනවා, කවදාවත් Gemini/Groq එකට direct නෑ.

## 🔍 Code Walkthrough
Methods දෙකයි:
- `complete(prompt, *, system=None, temperature=0.0) -> str` — සාමාන්‍ය text උත්තරයක්.
- `complete_structured(prompt, schema: type[T], ...) -> T` — **schema-constrained** generation.
  `schema` එක generic (`type[T]`) — ඒ නිසා **domain එක Pydantic import කරන්නේ නෑ**; concrete schemas
  application layer එකේ ([`agents/schemas.py`](../../application/agents/schemas.md)) තියෙනවා.

`@runtime_checkable` නිසා `isinstance(x, LLMProvider)` වැඩ කරනවා (structural check).

## 🔗 සම්බන්ධතා
- **Implement කරන්නේ:** [`adapters/llm/base.py`](../../adapters/llm/base.md) (+ gemini/groq), සහ
  [`infrastructure/llm_gateway.py`](../../infrastructure/llm_gateway.md) (decorator එකකුත් මේ port එකමයි).
- **Use කරන්නේ:** හැම LLM agent එකක්ම (A1, A2, A3, A5, A6, B2).

## 💡 Design decision
**Synchronous** (async නෙවෙයි) — async/SSE කරන්නේ API/graph layer එකේ. මේ port එක සරලව තියාගන්නවා.
