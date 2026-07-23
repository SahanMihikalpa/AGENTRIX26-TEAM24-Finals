"""Server-Sent Events: translate a LangGraph run into the doc/11 event stream.

The compiled graph is **synchronous**; we iterate ``graph.stream(stream_mode=
"updates")`` (which yields ``{node: update}`` per node) and translate each chunk
into SSE events. Starlette runs the producing generator in a worker thread, so the
graph and its checkpointer execute off the event loop without a manual bridge.

Event mapping (doc/11 §SSE):

* node → ``step`` pill transitions (`understand`/`find`/`ask`/`lookup`/`prepare`)
* ``enter_gap`` → ``gap`` *researching*; ``b3`` (kb updated) → ``gap`` *updated*
* ``a6`` answer → ``action_pack`` (+ ``message`` carrying the fallback text)
* ``__interrupt__`` → ``clarify`` (the interview pauses; the client re-POSTs to resume)
* end → ``done``; any exception → ``error``
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from app.api.dto import ActionPackDTO

# node → progress pill (doc/11 agent-step ↔ pill mapping)
_PILL: dict[str, str] = {
    "a1": "understand",
    "a2": "find",
    "a3": "ask",
    "clarify": "ask",
    "a4": "lookup",
    "a5": "lookup",
    "enter_gap": "lookup",
    "b1": "lookup",
    "b2": "lookup",
    "b3": "lookup",
    "b4": "lookup",
    # A cache hit delivers the pack without retrieving anything, so it advances
    # straight to "prepare" — the pill row stays honest about what actually ran.
    "cache_lookup": "prepare",
    "a6": "prepare",
    "persist_answer": "prepare",
}

# Nodes that can put a finished Action Pack on the state: A6 composes one, and
# cache_lookup replays one (AD-12). Both must reach the client identically — a
# cache hit is an implementation detail, not a different kind of answer.
_ANSWER_NODES = frozenset({"a6", "cache_lookup"})


def format_sse(event: str, data: dict[str, Any]) -> str:
    """Render one SSE frame: ``event: <name>\\n data: <json>\\n\\n``."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


class EventTranslator:
    """Stateful translator from graph ``updates`` chunks to SSE frames."""

    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        self._current_pill: str | None = None
        self.interrupted = False

    def translate(self, chunk: dict[str, Any]) -> Iterable[str]:
        """Yield the SSE frames for one ``{node: update}`` (or interrupt) chunk."""
        if "__interrupt__" in chunk:
            payload = chunk["__interrupt__"][0].value
            self.interrupted = True
            yield format_sse(
                "clarify",
                {
                    "question": payload.get("question", ""),
                    "options": payload.get("options", []),
                    "allow_free_text": payload.get("allow_free_text", True),
                },
            )
            return

        for node, update in chunk.items():
            has_answer = (
                node in _ANSWER_NODES and isinstance(update, dict) and update.get("answer")
            )
            # A cache_lookup *miss* returns {} — don't advance the pill to
            # "prepare"/"lookup" for a node that did nothing visible.
            pill = _PILL.get(node)
            if pill is not None and (node != "cache_lookup" or has_answer):
                yield from self._advance_pill(pill)

            if node == "enter_gap":
                yield format_sse(
                    "gap", {"phase": "researching", "text": "Searching official sources…"}
                )
            elif node == "b3" and isinstance(update, dict) and update.get("kb_updated"):
                yield format_sse(
                    "gap", {"phase": "updated", "text": "Knowledge base updated"}
                )
            elif has_answer and isinstance(update, dict):
                yield from self._answer_frames(update["answer"])

    def finalize(self) -> Iterable[str]:
        """Close the run: mark the last pill done (unless paused) and emit ``done``."""
        if not self.interrupted and self._current_pill is not None:
            yield format_sse("step", {"id": self._current_pill, "status": "done"})
        yield format_sse("done", {"session_id": self._session_id})

    # ── helpers ──────────────────────────────────────────────────
    def _advance_pill(self, pill: str) -> Iterable[str]:
        if pill == self._current_pill:
            return
        if self._current_pill is not None:
            yield format_sse("step", {"id": self._current_pill, "status": "done"})
        yield format_sse("step", {"id": pill, "status": "active"})
        self._current_pill = pill

    def _answer_frames(self, answer: dict[str, Any]) -> Iterable[str]:
        if answer.get("fallback") and answer.get("fallback_message"):
            yield format_sse(
                "message", {"role": "assistant", "text": answer["fallback_message"]}
            )
        yield format_sse("action_pack", ActionPackDTO.model_validate(answer).model_dump())
