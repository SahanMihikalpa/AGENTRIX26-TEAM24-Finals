# `application/graph/dependencies.py` — `GraphDependencies` (DI bundle)

**Layer:** application/graph · **Stage:** 4/5 · **Pattern:** Dependency Injection

## 🎯 කාර්යය
Graph එක build කරන්න ඕන **ports + tunables** එකතුව එක frozen dataclass එකක. Graph builder එක
**framework-pure + config-free** තියාගන්නවා — concrete adapters හෝ `Settings` import කරන්නේ නෑ.

## 🔍 Code Walkthrough
`GraphDependencies` (frozen):
- **Ports:** `llm`, `embedder`, `store`, `retriever`, `source_pool`, `web_search?`.
- **Tunables (defaults = Settings mirror):** `confidence_threshold` (τ, AD-8), `max_acquisition_loops`
  (N, AD-2), `top_k`, `max_questions`, `grader_sufficient_above`/`gap_below`, `web_allowlist` (QA-7).

## 🔗 සම්බන්ධතා
- **Build කරන්නේ:** [`api/runtime.py`](../../api/runtime.md) (real adapters + Settings) — edge එකේදී.
  Tests: fakes වලින්.
- **Use කරන්නේ:** [`builder.py`](builder.md) (`build_graph(deps)`).

## 💡 Design decision
`store` සහ `retriever` **වෙනම ports** (per-agent narrow dependency) ඒත් සාමාන්‍යයෙන් **එකම object**
(`ChromaSqliteStore` දෙකම implement කරනවා). Config එක edge එකේ resolve වෙනවා → application layer එක
`Settings` වලින් නිදහස්.
