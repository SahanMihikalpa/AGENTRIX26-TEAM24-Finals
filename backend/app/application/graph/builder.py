"""Stage 5 · LangGraph wiring — assemble the agents into the supervised graph.

This is the **only** place LangGraph is imported. It builds the hierarchical
multi-agent graph (docs/02): the Answering team ``A1→A6`` plus the bounded
Knowledge-Acquisition loop ``B1→B4``, with a **state-driven supervisor** expressed
as conditional edges (the supervisor doc) and A3's human-in-the-loop interview as a
LangGraph ``interrupt()``.

Routing is deterministic and cheap — every transition is a function of
``GraphState`` (zero LLM quota on plumbing). Loop bookkeeping (the AD-2 cap) lives
in the ``enter_gap`` wiring node, not in the agents, which stay framework-free.

The AD-12 query→answer cache is woven in as three wiring nodes (``cache_lookup`` /
``cache_store`` / ``cache_invalidate``) that are **no-ops when no cache is injected**,
so the topology is identical with or without one. ``cache_lookup`` sits *after*
resolution (A2/A3), where ``service+variant+district`` is known; the gap-loop
re-entry (``B4 → A4``) deliberately bypasses it to always re-retrieve fresh.

```
START → A1 → A2 ┬─ unknown ─────────────→ cache_lookup ┬─ hit ─→ END
                └─ known → A3 ⇄ clarify ─↗              └─ miss → A4 → A5
A4 → A5 ┬─ SUFFICIENT ──────────────────→ A6 → cache_store → END
        ├─ GAP, loops<N → enter_gap → B1→B2→B3 → cache_invalidate → B4 → A4
        └─ GAP, loops≥N ────────────────→ A6 (fallback) → cache_store → END
```
"""

from __future__ import annotations

from collections.abc import Callable
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
from app.domain.ports.cache import AnswerCache


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
        "a2": ServiceIdentifierAgent(deps.store, deps.llm),
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
    # AD-12 cache wiring nodes (no-ops when deps.cache is None → topology unchanged).
    # Typed Any (like the agent nodes) so LangGraph's node overloads resolve.
    cache_nodes: dict[str, Any] = {
        "cache_lookup": _make_cache_lookup(deps.cache),
        "cache_store": _make_cache_store(deps.cache),
        "cache_invalidate": _make_cache_invalidate(deps.cache),
    }
    for name, cache_node in cache_nodes.items():
        graph.add_node(name, cache_node)

    graph.add_edge(START, "a1")
    graph.add_edge("a1", "a2")
    graph.add_conditional_edges(
        "a2", _route_after_identify, {"a3": "a3", "cache_lookup": "cache_lookup"}
    )
    graph.add_conditional_edges(
        "a3", _route_after_clarify, {"clarify": "clarify", "cache_lookup": "cache_lookup"}
    )
    graph.add_edge("clarify", "a3")
    # Cache short-circuit: a hit serves the cached answer and ends; a miss retrieves.
    graph.add_conditional_edges("cache_lookup", _route_after_cache, {"a4": "a4", "end": END})
    graph.add_edge("a4", "a5")
    graph.add_conditional_edges(
        "a5",
        partial(_route_after_grade, max_loops=deps.max_acquisition_loops),
        {"a6": "a6", "enter_gap": "enter_gap"},
    )
    graph.add_edge("enter_gap", "b1")
    graph.add_edge("b1", "b2")
    graph.add_edge("b2", "b3")
    graph.add_edge("b3", "cache_invalidate")  # drop stale cache after a KB upsert
    graph.add_edge("cache_invalidate", "b4")
    graph.add_edge("b4", "a4")  # re-retrieve fresh (deliberately bypasses cache_lookup)
    graph.add_edge("a6", "cache_store")
    graph.add_edge("cache_store", END)

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


# ── AD-12 cache nodes (closures over the optional cache; no-op when absent) ──
def _make_cache_lookup(
    cache: AnswerCache | None,
) -> Callable[[GraphState], dict[str, Any]]:
    def cache_lookup(state: GraphState) -> dict[str, Any]:
        if cache is None or state["service_id"] is None:
            return {}  # disabled, or no resolved service to key on → miss
        answer = cache.get_answer(
            state["service_id"],
            variant_id=state["variant_id"],
            district=state["slots"].get("district"),
        )
        if answer is None:
            return {}
        # Replay the cached answer (+ its citations); routing then ends the run.
        return {"answer": answer, "citations": answer.get("citations", [])}

    return cache_lookup


def _make_cache_store(
    cache: AnswerCache | None,
) -> Callable[[GraphState], dict[str, Any]]:
    def cache_store(state: GraphState) -> dict[str, Any]:
        answer = state["answer"]
        # Cache only a real, served pack (never a fallback) for a resolved service.
        if cache is None or state["service_id"] is None or answer is None:
            return {}
        if answer.get("fallback"):
            return {}
        cache.put_answer(
            state["service_id"],
            answer,
            variant_id=state["variant_id"],
            district=state["slots"].get("district"),
        )
        return {}

    return cache_store


def _make_cache_invalidate(
    cache: AnswerCache | None,
) -> Callable[[GraphState], dict[str, Any]]:
    def cache_invalidate(state: GraphState) -> dict[str, Any]:
        if cache is not None and state["kb_updated"] and state["service_id"] is not None:
            cache.invalidate_service(state["service_id"])
        return {}

    return cache_invalidate


# ── supervisor routers (pure functions of state) ────────────────────
def _route_after_identify(state: GraphState) -> str:
    # No service to clarify when it's unknown — straight to the cache check (which
    # misses without a service_id) → retrieve → grade → gap.
    return "cache_lookup" if state["service_unknown"] else "a3"


def _route_after_clarify(state: GraphState) -> str:
    return "clarify" if state["pending_question"] is not None else "cache_lookup"


def _route_after_cache(state: GraphState) -> str:
    """A cache hit set ``answer`` → serve it and end; a miss → retrieve (A4)."""
    return "end" if state["answer"] is not None else "a4"


def _route_after_grade(state: GraphState, *, max_loops: int) -> str:
    if state["grade"] == Grade.SUFFICIENT.value:
        return "a6"
    if state["acquisition_loops"] < max_loops:
        return "enter_gap"
    return "a6"  # loop exhausted → A6 renders the graceful fallback (grade stays GAP)
