"""Stage 5 · the compiled graph, driven end-to-end with fakes.

These are integration tests over the real LangGraph ``StateGraph``: the happy path,
the self-expanding gap loop, the bounded fallback, and the A3 interrupt/resume.
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.application.agents.schemas import (
    ActionSteps,
    ClarificationQuestion,
    CuratedExtraction,
    CuratedFee,
    CuratedOffice,
    CuratedRequirement,
    IntentEntities,
    IntentExtraction,
    ServiceDisambiguation,
)
from app.application.graph import GraphDependencies, new_state
from app.application.graph.builder import build_graph
from app.domain.entities import SourceType
from app.domain.ports.cache import AnswerCache
from app.domain.ports.source_pool import PooledDocument
from app.infrastructure.cache import InMemoryAnswerCache
from tests.application.conftest import (
    DeterministicEmbedder,
    FakeSourcePool,
    ScriptedLLM,
    SeededKB,
)


def _deps(
    kb: SeededKB,
    embedder: DeterministicEmbedder,
    llm: ScriptedLLM,
    *,
    source_pool: FakeSourcePool | None = None,
    max_loops: int = 2,
    cache: AnswerCache | None = None,
) -> GraphDependencies:
    return GraphDependencies(
        llm=llm,
        embedder=embedder,
        store=kb.store,
        retriever=kb.store,
        source_pool=source_pool or FakeSourcePool(),
        web_allowlist=["gov.lk"],
        max_acquisition_loops=max_loops,
        grader_sufficient_above=0.4,  # robust against DeterministicEmbedder variance
        cache=cache,
    )


def _config(thread: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread}}


def test_happy_path_answers_a_seeded_service(
    kb: SeededKB, embedder: DeterministicEmbedder
) -> None:
    llm = ScriptedLLM(
        structured={
            IntentExtraction: IntentExtraction(
                normalized_query="land deed transfer", service_guess="land_deed_transfer"
            ),
            # "land deed transfer" now keyword-matches both seeded land services, so A2
            # disambiguates between them.
            ServiceDisambiguation: ServiceDisambiguation(
                service_id=kb.deed_service_id, confidence=0.9
            ),
            ActionSteps: ActionSteps(steps=["Collect documents", "Visit DS Galle"]),
        }
    )
    app = build_graph(_deps(kb, embedder, llm), checkpointer=MemorySaver())

    state = new_state("t1", "I want to transfer my inherited land")
    state["slots"] = {"condition": "inheritance", "district": "Galle"}
    result = app.invoke(state, _config("t1"))

    answer = result["answer"]
    assert result["grade"] == "SUFFICIENT"
    assert answer["fallback"] is False
    assert answer["service_label"] == "Land Deed Transfer (inheritance)"
    assert [doc["name"] for doc in answer["documents"]] == ["Death certificate"]
    assert answer["verification"] == "verified"


def test_gap_loop_acquires_unseen_service_then_answers(
    kb: SeededKB, embedder: DeterministicEmbedder
) -> None:
    pool = FakeSourcePool(
        [
            PooledDocument(
                text="business name registration needs nic copy fee colombo",
                title="Business Reg Circular",
                source_type=SourceType.CIRCULAR,
                url="https://reg.gov.lk/biz",
            )
        ]
    )
    extraction = CuratedExtraction(
        service_name="Business Name Registration",
        service_slug="business_name_registration",
        category="business",
        description="Register a business name",
        condition_label="standard",
        requirements=[CuratedRequirement(document_name="NIC copy")],
        fees=[CuratedFee(label="Registration fee", amount_lkr="2000")],
        offices=[CuratedOffice(name="DS Colombo", district="Colombo", address="Town Hall")],
        district="Colombo",
        extraction_confidence=0.9,
    )
    llm = ScriptedLLM(
        structured={
            IntentExtraction: IntentExtraction(
                normalized_query="business name registration",
                service_guess="business_name_registration",
            ),
            CuratedExtraction: extraction,
            ActionSteps: ActionSteps(steps=["Bring your NIC copy", "Pay LKR 2000"]),
        }
    )
    app = build_graph(_deps(kb, embedder, llm, source_pool=pool), checkpointer=MemorySaver())

    result = app.invoke(new_state("t2", "how do I register a business name"), _config("t2"))

    answer = result["answer"]
    assert result["kb_updated"] is True
    assert result["service_unknown"] is False  # B3 handed the new service back
    assert answer["fallback"] is False
    assert answer["verification"] == "newly_gathered_pending_verification"
    assert [doc["name"] for doc in answer["documents"]] == ["NIC copy"]
    # the KB genuinely grew, and the auto-gathered source is queued for moderation
    assert any(s.slug == "business_name_registration" for s in kb.store.find_services("business"))
    assert len(result["moderation_queue"]) == 1


def test_gap_loop_exhausts_to_graceful_fallback(
    kb: SeededKB, embedder: DeterministicEmbedder
) -> None:
    # Nothing in the pool and no web search → the loop finds nothing and caps out.
    llm = ScriptedLLM(
        structured={
            IntentExtraction: IntentExtraction(
                normalized_query="dragon licence", service_guess="dragon_licence"
            )
        }
    )
    app = build_graph(_deps(kb, embedder, llm, max_loops=2), checkpointer=MemorySaver())

    result = app.invoke(new_state("t3", "I need a dragon licence"), _config("t3"))

    assert result["acquisition_loops"] == 2  # bounded by N
    assert result["answer"]["fallback"] is True


def test_clarification_interrupts_then_resumes(
    kb: SeededKB, embedder: DeterministicEmbedder
) -> None:
    llm = ScriptedLLM(
        structured={
            IntentExtraction: IntentExtraction(
                normalized_query="land deed transfer",
                service_guess="land_deed_transfer",
                entities=IntentEntities(district="Galle"),  # district known, variant not
            ),
            ServiceDisambiguation: ServiceDisambiguation(
                service_id=kb.deed_service_id, confidence=0.9
            ),
            ClarificationQuestion: ClarificationQuestion(
                question="Is this an inheritance, sale, or gift?"
            ),
            ActionSteps: ActionSteps(steps=["Collect documents", "Visit DS Galle"]),
        }
    )
    app = build_graph(_deps(kb, embedder, llm), checkpointer=MemorySaver())
    config = _config("t4")

    first = app.invoke(new_state("t4", "transfer my land"), config)

    interrupt = first["__interrupt__"][0]
    assert interrupt.value["slot"] == "condition"
    assert set(interrupt.value["options"]) == {"inheritance", "sale"}

    result = app.invoke(Command(resume="inheritance"), config)

    answer = result["answer"]
    assert answer["fallback"] is False
    assert answer["service_label"] == "Land Deed Transfer (inheritance)"


# ── AD-12 cache (Stage 7b) ───────────────────────────────────────
def _steps_calls(llm: ScriptedLLM) -> int:
    return sum(1 for _, name in llm.calls if name == "ActionSteps")


def test_cache_hit_short_circuits_generation(
    kb: SeededKB, embedder: DeterministicEmbedder
) -> None:
    cache = InMemoryAnswerCache()
    llm = ScriptedLLM(
        structured={
            IntentExtraction: IntentExtraction(
                normalized_query="land deed transfer", service_guess="land_deed_transfer"
            ),
            ActionSteps: ActionSteps(steps=["Collect documents"]),
        }
    )
    app = build_graph(_deps(kb, embedder, llm, cache=cache), checkpointer=MemorySaver())

    state1 = new_state("h1", "transfer inherited land")
    state1["slots"] = {"condition": "inheritance", "district": "Galle"}
    app.invoke(state1, _config("h1"))
    assert _steps_calls(llm) == 1  # generated once, now cached

    state2 = new_state("h2", "transfer inherited land")
    state2["slots"] = {"condition": "inheritance", "district": "Galle"}
    result = app.invoke(state2, _config("h2"))

    assert _steps_calls(llm) == 1  # A6 NOT re-run → answer served from the cache
    assert result["answer"]["service_label"] == "Land Deed Transfer (inheritance)"
    assert len(cache) == 1


def test_fallback_answers_are_not_cached(
    kb: SeededKB, embedder: DeterministicEmbedder
) -> None:
    cache = InMemoryAnswerCache()
    llm = ScriptedLLM(
        structured={
            IntentExtraction: IntentExtraction(
                normalized_query="dragon licence", service_guess="dragon_licence"
            )
        }
    )
    app = build_graph(
        _deps(kb, embedder, llm, max_loops=1, cache=cache), checkpointer=MemorySaver()
    )

    result = app.invoke(new_state("f1", "I need a dragon licence"), _config("f1"))

    assert result["answer"]["fallback"] is True
    assert len(cache) == 0  # never cache a fallback → the next try can still succeed
