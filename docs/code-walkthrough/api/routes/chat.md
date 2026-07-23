# `api/routes/chat.py` — Chat SSE + Action-Pack fetch

**Layer:** api/routes · **Stage:** 6 · [docs/11 §2](../../../11-frontend-architecture.md)

## 🎯 කාර්යය
Main citizen-facing endpoint. `POST /api/chat` — එක agent run එක **SSE** විදියට stream කරනවා; A3 interview
resume කරන්නේ එකම `session_id` එකෙන් තව call එකක් (checkpointer නිසා resumable).

## 🔍 Code Walkthrough
- **`POST /api/chat`** — `session_id` (නැත්නම් `uuid4`) → `StreamingResponse(_run(...), media_type=
  "text/event-stream")` (no-cache headers).
- **`GET /api/sessions/{id}/action-pack`** — session එකේ final ActionPack (`snapshot.values["answer"]`),
  නැත්නම් 404.
- **`_run`** — `graph.stream(input, config, stream_mode="updates")` iterate → `EventTranslator` frames yield
  → `finalize()`. Exception → graceful **`error`** SSE frame (torn 500 නෙවෙයි).
- **`_graph_input`** — snapshot එකේ `next` තියෙනවා නම් (A3 interrupt එකේ paused) → **`Command(resume=message)`**
  (citizen answer feed back); නැත්නම් `new_state(...)` (fresh run).

## 🔗 සම්බන්ධතා
[runtime](../runtime.md) (`get_runtime` DI), [sse](../sse.md) (`EventTranslator`),
[session_state](../session_state.md), [builder](../../application/graph/builder.md) (graph).

## 💡 Design decision — resume = same endpoint
POST + resume එකම endpoint එකෙන් — `Command(resume=...)` + checkpointer නිසා. Sync generator, Starlette
worker thread (graph off event-loop).
