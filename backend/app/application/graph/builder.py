"""Stage 5 · LangGraph wiring — assemble the agents into the supervised graph.

This is the **only** place LangGraph is imported. It builds the hierarchical
multi-agent graph (docs/02): the Answering team ``A1→A6`` plus the bounded
Knowledge-Acquisition loop ``B1→B4``, with a **state-driven supervisor** expressed
as conditional edges (the supervisor doc) and A3's human-in-the-loop interview as a
LangGraph ``interrupt()``.

Routing is deterministic and cheap — every transition is a function of
``GraphState`` (zero LLM quota on plumbing). Loop bookkeeping (the AD-2 cap) lives
in the ``enter_gap`` wiring node, not in the agents, which stay framework-free.

```
START → A1 → A2 ┬─ unknown ──────────────────────────→ A4
                └─ known → A3 ⇄ clarify → cache_lookup ┬─ miss → A4
                                                       └─ hit ────────────→ END

A4 → A5 ┬─ SUFFICIENT ────────→ A6 → persist_answer → END
        ├─ GAP, loops < N ────→ enter_gap → B1 → B2 → B3 → invalidate_cache → B4 → A4
        └─ GAP, loops ≥ N ────→ A6 (fallback) → persist_answer → END
```

``cache_lookup``/``persist_answer`` implement AD-12: once the interview has pinned
``service + variant + district``, an identical earlier question is answered without
paying for A5's grading call or A6's composition call. ``invalidate_cache`` closes
the staleness hole — B3 growing the KB drops that service's cached answers. The
unknown-service branch skips the cache entirely: there is no key to look up.

``persist_answer`` also writes the served pack to the ``checklist`` table, the
durable record that outlives the thread's checkpoint.
"""

from __future__ import annotations

import logging
from functools import partial
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.application.agents import (
    ActionPackAgent,
    ClarificationAgent,
    ExtractCurateAgent,
    GapGraderAgent,
    IntakeIntentAgent,
    KBUpdaterAgent,
    ModerationGateAgent,
    ResearchAgent,
    RetrievalAgent,
    ServiceIdentifierAgent,
)
from app.application.graph.dependencies import GraphDependencies
from app.application.graph.state import GraphState
from app.domain.entities import Grade
from app.domain.ports.cache import AnswerCache, CacheKey
from app.domain.ports.knowledge import KnowledgeStore

_log = logging.getLogger(__name__)


def build_graph(deps: GraphDependencies, *, checkpointer: Any = None) -> Any:
    """Construct and compile the agent graph from injected dependencies.

    A ``checkpointer`` (e.g. ``SqliteSaver``) is required for the A3 interview to
    pause/resume across requests; pass ``MemorySaver`` in tests or ``None`` for a
    one-shot run with no clarification.
    """
    # Heterogeneous agent instances; typed Any so LangGraph's node overloads resolve
    # (each agent's own __call__ signature is type-checked at its definition).
    nodes: dict[str, Any] = {
        "a1": IntakeIntentAgent(deps.llm),
        "a2": ServiceIdentifierAgent(
            deps.store, deps.llm, confidence_threshold=deps.confidence_threshold
        ),
        "a3": ClarificationAgent(deps.store, deps.llm, max_questions=deps.max_questions),
        "a4": RetrievalAgent(deps.embedder, deps.retriever, top_k=deps.top_k),
        "a5": GapGraderAgent(
            deps.llm,
            sufficient_above=deps.grader_sufficient_above,
            gap_below=deps.grader_gap_below,
        ),
        "a6": ActionPackAgent(
            deps.store, deps.llm, confidence_threshold=deps.confidence_threshold
        ),
        "b1": ResearchAgent(
            deps.source_pool,
            deps.web_search,
            allowlist=deps.web_allowlist,
            max_results=deps.top_k,
        ),
        "b2": ExtractCurateAgent(deps.llm),
        "b3": KBUpdaterAgent(deps.store, deps.embedder),
        "b4": ModerationGateAgent(confidence_threshold=deps.confidence_threshold),
    }

    graph = StateGraph(GraphState)
    for name, node in nodes.items():
        graph.add_node(name, node)
    graph.add_node("clarify", _clarify_node)
    graph.add_node("enter_gap", _enter_gap_node)
    graph.add_node("cache_lookup", partial(_cache_lookup_node, cache=deps.answer_cache))
    graph.add_node(
        "persist_answer",
        partial(_persist_answer_node, cache=deps.answer_cache, store=deps.store),
    )
    graph.add_node(
        "invalidate_cache", partial(_invalidate_cache_node, cache=deps.answer_cache)
    )

    graph.add_edge(START, "a1")
    graph.add_edge("a1", "a2")
    graph.add_conditional_edges("a2", _route_after_identify, {"a3": "a3", "a4": "a4"})
    graph.add_conditional_edges(
        "a3", _route_after_clarify, {"clarify": "clarify", "cache_lookup": "cache_lookup"}
    )
    graph.add_edge("clarify", "a3")
    graph.add_conditional_edges("cache_lookup", _route_after_cache, {"a4": "a4", END: END})
    graph.add_edge("a4", "a5")
    graph.add_conditional_edges(
        "a5",
        partial(_route_after_grade, max_loops=deps.max_acquisition_loops),
        {"a6": "a6", "enter_gap": "enter_gap"},
    )
    graph.add_edge("enter_gap", "b1")
    graph.add_edge("b1", "b2")
    graph.add_edge("b2", "b3")
    graph.add_edge("b3", "invalidate_cache")
    graph.add_edge("invalidate_cache", "b4")
    graph.add_edge("b4", "a4")
    graph.add_edge("a6", "persist_answer")
    graph.add_edge("persist_answer", END)

    return graph.compile(checkpointer=checkpointer)


# ── wiring-only nodes (supervisor bookkeeping; not agents) ───────────
def _clarify_node(state: GraphState) -> dict[str, Any]:
    """Surface A3's question to the UI and pause; on resume, fill the answered slot."""
    question = state["pending_question"]
    if question is None:  # defensive — routing should never bring us here
        return {}
    answer = interrupt(question)  # pauses; resumes via Command(resume=answer)
    slot = str(question.get("slot", "condition"))
    return {"slots": {**state["slots"], slot: answer}, "pending_question": None}


def _enter_gap_node(state: GraphState) -> dict[str, Any]:
    """Commit to one acquisition loop: bump the cap counter, reset per-loop scratch."""
    return {
        "acquisition_loops": state["acquisition_loops"] + 1,
        "acquisition_buffer": [],
        "curated": [],
        "kb_updated": False,
    }


def _cache_key(state: GraphState) -> CacheKey | None:
    """The AD-12 key for this run, or ``None`` when the service is not pinned."""
    service_id = state["service_id"]
    if service_id is None:
        return None
    district = state["slots"].get("district")
    return CacheKey.build(
        service_id,
        variant_id=state["variant_id"],
        district=str(district) if district else None,
    )


def _cache_lookup_node(
    state: GraphState, *, cache: AnswerCache | None
) -> dict[str, Any]:
    """Answer straight from the cache when this exact question was asked before.

    A hit populates ``answer``/``citations`` and the router sends the run to END,
    skipping A4→A5→A6 — the two LLM calls this whole mechanism exists to avoid.
    """
    if cache is None:
        return {}
    key = _cache_key(state)
    if key is None:
        return {}
    answer = cache.get(key)
    if answer is None:
        return {}
    return {"answer": answer, "citations": answer.get("citations", [])}


def _persist_answer_node(
    state: GraphState, *, cache: AnswerCache | None, store: KnowledgeStore
) -> dict[str, Any]:
    """Remember A6's Action Pack — durably, and in the cache.

    Two different lifetimes, one moment: the ``checklist`` row is the permanent
    record of what a citizen was actually told (it outlives the checkpoint), while
    the cache is the in-process short-circuit for the next identical question.

    Fallback packs are written to ``checklist`` but deliberately **not** cached:
    they are the "we could not verify this" placeholder, and the next run — after
    the KB has grown — should get a real answer, not the stale apology.
    """
    answer = state["answer"]
    if not answer:
        return {}

    try:
        store.save_checklist(
            state["session_id"],
            answer,
            service_id=state["service_id"],
            variant_id=state["variant_id"],
        )
    except Exception:
        _log.exception("Could not persist the checklist for session %s", state["session_id"])

    if cache is not None and not answer.get("fallback"):
        key = _cache_key(state)
        if key is not None:
            cache.put(key, answer)
    return {}


def _invalidate_cache_node(
    state: GraphState, *, cache: AnswerCache | None
) -> dict[str, Any]:
    """Drop the service's cached answers once B3 has written new knowledge (AD-12).

    Without this, a gap loop could expand the KB and the *next* citizen would
    still be served the pre-expansion answer for a neighbouring district/variant.
    """
    if cache is not None and state["kb_updated"] and state["service_id"] is not None:
        cache.invalidate_service(state["service_id"])
    return {}


# ── supervisor routers (pure functions of state) ────────────────────
def _route_after_identify(state: GraphState) -> str:
    # No service to clarify when it's unknown — go straight to retrieve→grade→gap.
    return "a4" if state["service_unknown"] else "a3"


def _route_after_clarify(state: GraphState) -> str:
    # Interview done → the service/variant/district are pinned, which is exactly
    # when a cache key exists to try.
    return "clarify" if state["pending_question"] is not None else "cache_lookup"


def _route_after_cache(state: GraphState) -> str:
    return END if state["answer"] is not None else "a4"


def _route_after_grade(state: GraphState, *, max_loops: int) -> str:
    if state["grade"] == Grade.SUFFICIENT.value:
        return "a6"
    if state["acquisition_loops"] < max_loops:
        return "enter_gap"
    return "a6"  # loop exhausted → A6 renders the graceful fallback (grade stays GAP)
