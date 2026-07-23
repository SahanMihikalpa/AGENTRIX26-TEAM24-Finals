# `api/runtime.py` — Composition root (wire everything)

**Layer:** api · **Stage:** 6 · **Pattern:** Composition Root / DI

## 🎯 කාර්යය
Concrete adapters ඔක්කොම → runnable graph එකට assemble කරන **එකම තැන**. `Settings` **සහ** concrete adapters
දෙකම දන්නා single place — application/graph layers config- + adapter-free තියෙනවා.

## 🔍 Code Walkthrough
- **`AppRuntime`** (frozen) — wired backend: `graph` (compiled), `store`, `cache`, `settings`,
  `experience_intake`, `moderation`.
- **`build_runtime(settings)`** — store (ChromaSqlite), llm (`_build_llm`), embedder (bge), `GraphDependencies`
  (ports + tunables inject) → `build_graph(deps, checkpointer)`. Web search, source pool, use cases wire.
- **`get_runtime(request)`** — FastAPI dependency: runtime **lazily build + cache** on `app.state` (first
  `/api/chat` request එක warm-up pay කරනවා). **Tests මේක override** කරනවා → real stores/network නෑ.
- **`_build_llm`** — Gemini primary + optional Groq fallback → **`LLMGateway`** එකෙන් wrap (rate-limit).
- **`_build_web_search`** — Tavily key තිබුණොත් Tavily, නැත්නම් DDG.
- **`_build_checkpointer`** — persistent `SqliteSaver` (A3 interview cross-request resume, AD-3).

## 💡 Design decision
Composition root එකෙන් hexagonal boundary එක close වෙනවා — dependency rule එකේ **edge** එක. Lazy + key-free
`build_runtime` → cheap to call. `store` දෙපැත්තෙන්ම (`store` + `retriever`) inject වෙනවා (same object).

## 🔗 සම්බන්ධතා
Adapters ↔ [gateway](../infrastructure/llm_gateway.md) ↔ [builder](../application/graph/builder.md). Used by
every route via `get_runtime`.
