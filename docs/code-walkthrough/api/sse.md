# `api/sse.py` — Server-Sent Events translator

**Layer:** api · **Stage:** 6 · [docs/11 §SSE](../../11-frontend-architecture.md)

## 🎯 කාර්යය
LangGraph run එකක් → frontend එකට යන **SSE event stream** එකට translate කිරීම. Graph එක **synchronous** —
`graph.stream(stream_mode="updates")` iterate කරලා (`{node: update}` per node), එක එක chunk එක SSE event
වලට map. Starlette generator එක worker thread එකක run කරනවා → graph + checkpointer event loop එකෙන් පිට.

## 🔍 Code Walkthrough
- `format_sse(event, data)` — එක SSE frame (`event: <name>\ndata: <json>\n\n`).
- **`_PILL`** — node → progress pill map (`a1`→understand, `a2`→find, `a3`→ask, `a4/a5/b*`→lookup, `a6`→prepare).
- **`EventTranslator(session_id)`** — stateful:
  - `translate(chunk)` — `__interrupt__` → **`clarify`** event (interview pause); node → **`step`** pill
    transitions; `enter_gap` → `gap` researching; `b3` (kb_updated) → `gap` updated; `a6` answer →
    **`action_pack`** (+ fallback → `message`).
  - `finalize()` — last pill `done` + **`done`** event.
  - `_advance_pill` — pill වෙනස් වුණාම කලින් එක `done`, අලුත් එක `active`.

## 🔗 සම්බන්ධතා
Used by [routes/chat.py](routes/chat.md) (`_run`). Answer → [`ActionPackDTO`](dto.md).

## 💡 Design decision
Sync graph + Starlette worker thread → manual async bridge එකක් නෑ. Error → graceful `error` SSE frame
(torn 500 එකක් නෙවෙයි).
