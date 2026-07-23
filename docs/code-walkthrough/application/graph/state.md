# `application/graph/state.py` — `GraphState` (the blackboard)

**Layer:** application/graph · **Stage:** 4 · **ADR:** AD-3 · **Pattern:** Blackboard

## 🎯 කාර්යය
හැම agent එකක්ම read/write කරන **shared state object** එක. එක flat, **JSON-serialisable** `TypedDict` එකක්
— graph එක හරහා flow වෙනවා, Stage 5 එකේ `SqliteSaver` checkpointer එකෙන් `thread_id` (= chat session)
එකට persist වෙනවා → A3 interview එක pause/resume කරන්න පුළුවන්.

## 🔍 Code Walkthrough
`GraphState(TypedDict)` — fields, agent අනුව group කරලා:
- **Input:** `session_id`, `user_query`.
- **A1:** `intent`. **A2:** `service_id`, `service_unknown`.
- **A3:** `variant_id`, `slots`, `pending_question` (`{slot, question, options, allow_free_text}`),
  `asked_slots`.
- **A4:** `retrieved` (scored chunks + provenance). **A5:** `grade`, `grade_reason`, `answer_confidence`.
- **Team 2:** `acquisition_loops` (cap counter), `acquisition_buffer`, `curated`, `kb_updated`,
  `moderation_queue`.
- **A6:** `answer` (serialized ActionPack), `citations`.

`new_state(session_id, user_query)` — හැම field එකක්ම empty default එකෙන් fresh state එකක්. Nodes
**partial `dict` updates** return කරනවා (LangGraph merge කරනවා).

## 💡 Design decisions
- **No LangGraph import** — pure `TypedDict`; agents framework-free callables `(GraphState) -> dict`.
- **Lean (AD-3):** හැම node එකකදීම checkpoint වෙනවා, ඒ නිසා **references + small artifacts විතරයි**.
  `retrieved` = chunk text + provenance (A5 grade කරන්න); exact rows A6 store එකෙන් කියවනවා (state bloat නෑ).
- Delta: `pending_question` structured dict (bare str නෙවෙයි) → UI `clarify` SSE event එකට 1:1 map.
