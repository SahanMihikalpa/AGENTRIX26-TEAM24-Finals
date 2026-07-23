# `adapters/llm/base.py` — LangChain LLM wrapper (shared base)

**Layer:** adapters · **Stage:** 3 · **Implements:** [`LLMProvider`](../../domain/ports/llm.md)

## 🎯 කාර්යය
ඕනම LangChain `BaseChatModel` එකක් → `LLMProvider` port එකට adapt කරන **shared base** එක. Gemini +
Groq දෙකම මේකෙන් extend වෙනවා, ඒ නිසා prompt→messages→invoke + structured-output logic එක **එක තැනක**.

## 🔍 Code Walkthrough
- **`LangChainLLMProvider(model_factory)`** — factory එකක් ගන්නවා (`temperature -> BaseChatModel`).
- **Per-temperature memoization:** LangChain temperature එක construction එකේදී fix කරනවා, ඒ නිසා distinct
  temperature එකකට model එකක් build කරලා **cache** කරනවා (`_models` dict). වැඩිපුර calls `0.0` — ඒ නිසා
  practice එකේදී එක cached model එකයි.
- **Import-free hot path:** messages `(role, content)` **tuples** විදියට යවනවා (valid `LanguageModelInput`)
  → මේ module එක import කරද්දී LangChain import වෙන්නේ නෑ → fake model එකකින් unit-test කරන්න පුළුවන්.
- `complete(...)` → text; `complete_structured(prompt, schema)` → `with_structured_output(schema).invoke(...)`
  (`cast(T, ...)`). `_content_to_text` — str හෝ multimodal parts list එකක් normalize.

## 🔗 සම්බන්ධතා
- **Extend කරන්නේ:** [`gemini.py`](gemini.md), [`groq.py`](groq.md).
- **Wrap කරන්නේ:** [`llm_gateway.py`](../../infrastructure/llm_gateway.md).

## 💡 Design decision
Shared base + thin providers = provider එකක් add/swap කරන්න lines කිහිපයයි (Strategy/Adapter). Structured
schema generic — domain Pydantic import කරන්නේ නෑ.
