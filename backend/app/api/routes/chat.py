"""Chat delivery — the SSE agent run and the Action-Pack fetch (doc/11 §2).

``POST /api/chat`` streams one agent run as SSE; resuming the A3 interview is just
another call with the same ``session_id`` (the checkpointer makes it resumable).
The producing generator is **synchronous** — Starlette iterates it in a worker
thread, so the graph and its SQLite checkpointer run off the event loop.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.types import Command

from app.api.dto import ActionPackDTO, ChatRequest
from app.api.runtime import AppRuntime, get_runtime
from app.api.session_state import thread_config
from app.api.sse import EventTranslator, format_sse
from app.application.graph import new_state

router = APIRouter(prefix="/api", tags=["chat"])

RuntimeDep = Annotated[AppRuntime, Depends(get_runtime)]


@router.post("/chat")
async def chat(request: ChatRequest, runtime: RuntimeDep) -> StreamingResponse:
    """Run (or resume) the agent graph for a session, streaming progress as SSE."""
    session_id = request.session_id or uuid4().hex
    return StreamingResponse(
        _run(runtime, session_id, request.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions/{session_id}/action-pack", response_model=ActionPackDTO)
async def get_action_pack(session_id: str, runtime: RuntimeDep) -> ActionPackDTO:
    """Fetch the final Action Pack for a session (fallback to the stream).

    The live checkpoint is the fast path; the persisted ``checklist`` row is the
    durable one, so a link to an Action Pack keeps working after the thread's
    checkpoint has been pruned.
    """
    snapshot = runtime.graph.get_state(thread_config(session_id))
    answer = snapshot.values.get("answer") if snapshot.values else None
    if not answer:
        answer = runtime.store.get_checklist(session_id)
    if not answer:
        raise HTTPException(status_code=404, detail="no action pack for this session")
    return ActionPackDTO.model_validate(answer)


# ── streaming internals ──────────────────────────────────────────
def _run(runtime: AppRuntime, session_id: str, message: str) -> Iterator[str]:
    config = thread_config(session_id)
    translator = EventTranslator(session_id)
    try:
        graph_input = _graph_input(runtime, config, session_id, message)
        for chunk in runtime.graph.stream(graph_input, config, stream_mode="updates"):
            yield from translator.translate(chunk)
        yield from translator.finalize()
    except Exception as exc:  # surface a graceful SSE error, never a torn 500 mid-stream
        yield format_sse("error", {"message": str(exc)})


def _graph_input(
    runtime: AppRuntime, config: dict[str, Any], session_id: str, message: str
) -> Any:
    """Resume a paused interview, or start a fresh run for a new query."""
    snapshot = runtime.graph.get_state(config)
    if snapshot.next:  # paused on the A3 interrupt → feed the citizen's answer back
        return Command(resume=message)
    return new_state(session_id, message)
