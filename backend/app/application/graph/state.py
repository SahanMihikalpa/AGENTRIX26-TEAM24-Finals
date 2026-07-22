"""``GraphState`` — the shared blackboard every agent reads and writes.

This is the **Blackboard / Data-Centred** state from
[docs/02 · state management](../../../docs/02-architecture.md#state-management-langgraph):
one flat, JSON-serialisable object that flows through the graph and (in Stage 5)
is persisted per ``thread_id`` by the ``SqliteSaver`` checkpointer.

Design rules honoured here:

* **Pure-ish:** a plain :class:`typing.TypedDict` — **no LangGraph import**. Agents
  are framework-free callables ``(GraphState) -> dict``; the ``StateGraph`` wiring,
  reducers and checkpointer arrive in Stage 5.
* **Lean (AD-3):** the state is checkpointed on every node, so only *references and
  small artifacts* live here. ``retrieved`` holds chunk text + provenance (what A5
  needs to grade); A6 re-reads the exact structured rows from the store rather than
  copying ``REQUIREMENT/FEE/OFFICE`` data into the persisted state.

Deltas vs. the illustrative ``GraphState`` in docs/02 (logged in docs/10):

* ``service_id`` / ``variant_id`` are ``int | None`` (the catalog uses integer PKs),
  not the doc's illustrative ``str``.
* ``pending_question`` is a structured dict ``{slot, question, options,
  allow_free_text}`` rather than a bare ``str`` — it maps 1:1 onto the doc/11
  ``clarify`` SSE event and tells the resume step which slot the answer fills.
* A handful of fields named in the agent docs are made explicit: ``service_unknown``
  (A2), ``grade_reason`` (A5), ``asked_slots`` (A3 guardrail), and the Team-2
  acquisition fields (``acquisition_buffer``, ``curated``, ``kb_updated``,
  ``moderation_queue``) consumed in Stage 4b.
"""

from __future__ import annotations

from typing import Any, TypedDict


class GraphState(TypedDict):
    """The single typed state object shared across the whole agent graph."""

    # ── identity / input ──────────────────────────────────────────
    session_id: str
    user_query: str

    # ── A1 · Intake & Intent ──────────────────────────────────────
    # {normalized_query, service_guess, entities, ambiguous}
    intent: dict[str, Any]

    # ── A2 · Service Identifier ───────────────────────────────────
    service_id: int | None
    service_unknown: bool

    # ── A3 · Clarification (slot-filling interview) ───────────────
    variant_id: int | None
    slots: dict[str, Any]
    # None when the interview is complete; otherwise a clarify payload for the UI.
    pending_question: dict[str, Any] | None
    asked_slots: list[str]  # guardrail: slots already asked, to cap the interview

    # ── A4 · Retrieval ────────────────────────────────────────────
    retrieved: list[dict[str, Any]]  # scored chunks + provenance (see serialization)

    # ── A5 · Gap Grader ───────────────────────────────────────────
    grade: str  # "" until graded, then "SUFFICIENT" | "GAP"
    grade_reason: str
    answer_confidence: float  # min confidence of supporting facts → A6 serving gate

    # ── Team 2 · Knowledge Acquisition (Stage 4b) ─────────────────
    acquisition_loops: int  # guardrail counter (cap N)
    acquisition_buffer: list[dict[str, Any]]  # B1 raw evidence → B2
    curated: list[dict[str, Any]]  # B2 curated records → B3
    kb_updated: bool  # B3 → supervisor re-runs A4
    moderation_queue: list[dict[str, Any]]  # B4 entries

    # ── A6 · Action Pack ──────────────────────────────────────────
    answer: dict[str, Any] | None  # serialized ActionPack
    citations: list[dict[str, Any]]


def new_state(session_id: str, user_query: str) -> GraphState:
    """Build a fresh :class:`GraphState` with every field at its empty default.

    The graph entry point uses this so each node can rely on keys existing (the
    ``TypedDict`` is total); nodes return *partial* ``dict`` updates that LangGraph
    merges in Stage 5.
    """
    return GraphState(
        session_id=session_id,
        user_query=user_query,
        intent={},
        service_id=None,
        service_unknown=False,
        variant_id=None,
        slots={},
        pending_question=None,
        asked_slots=[],
        retrieved=[],
        grade="",
        grade_reason="",
        answer_confidence=0.0,
        acquisition_loops=0,
        acquisition_buffer=[],
        curated=[],
        kb_updated=False,
        moderation_queue=[],
        answer=None,
        citations=[],
    )
