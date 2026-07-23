# `api/session_state.py` — Session checkpoint helpers

**Layer:** api · **Stage:** 6

## 🎯 කාර්යය
Session එකක checkpointed graph state එක read කරන tiny helpers දෙකක්. `session_id` = LangGraph
**`thread_id`** (SqliteSaver එක thread එකකට එක `GraphState` persist කරනවා).

## 🔍 Code Walkthrough
- `thread_config(session_id)` → `{"configurable": {"thread_id": session_id}}` — thread එකක් address කරන config.
- `session_values(graph, session_id)` → session එකේ latest checkpointed state (`graph.get_state(...)`),
  empty නම් `{}`.

## 🔗 සම්බන්ධතා
Use කරන්නේ [chat](routes/chat.md) (resume) + [feedback](routes/feedback.md) (session එකෙන් service/district
resolve).

## 💡 Design decision
Chat resume path එකට **සහ** experience-report intake එකට දෙකටම thread address + values read ඕන නිසා, මේ
common helpers දෙක එකම තැනක.
