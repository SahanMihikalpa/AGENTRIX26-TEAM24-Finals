"""A5 · Gap Grader — the two-stage Corrective-RAG switch."""

from __future__ import annotations

from typing import Any

from app.application.agents.a5_grader import GapGraderAgent
from app.application.agents.schemas import GradeDecision
from app.application.graph.state import GraphState, new_state
from tests.application.conftest import ScriptedLLM


def _chunk(score: float, *, confidence: float = 0.9, status: str = "verified") -> dict[str, Any]:
    return {
        "content": "stamp duty 1000",
        "score": score,
        "confidence": confidence,
        "verification_status": status,
        "source_id": 1,
    }


def _state(*, unknown: bool = False, retrieved: list[dict[str, Any]] | None = None) -> GraphState:
    state = new_state("s", "transfer land")
    state["service_unknown"] = unknown
    state["retrieved"] = retrieved or []
    return state


def test_unknown_service_is_immediate_gap() -> None:
    update = GapGraderAgent()(_state(unknown=True))
    assert update["grade"] == "GAP"
    assert update["answer_confidence"] == 0.0


def test_no_evidence_is_gap() -> None:
    update = GapGraderAgent()(_state(retrieved=[]))
    assert update["grade"] == "GAP"


def test_high_score_is_sufficient_and_carries_confidence() -> None:
    update = GapGraderAgent()(_state(retrieved=[_chunk(0.8, confidence=0.95)]))
    assert update["grade"] == "SUFFICIENT"
    assert update["answer_confidence"] == 0.95


def test_low_score_is_gap() -> None:
    update = GapGraderAgent()(_state(retrieved=[_chunk(0.1)]))
    assert update["grade"] == "GAP"


def test_borderline_without_llm_biases_to_gap() -> None:
    update = GapGraderAgent()(_state(retrieved=[_chunk(0.4)]))
    assert update["grade"] == "GAP"
    assert "borderline" in update["grade_reason"]


def test_borderline_with_llm_can_be_sufficient() -> None:
    decision = GradeDecision(grade="SUFFICIENT", confidence=0.7, reason="covers the need")
    agent = GapGraderAgent(ScriptedLLM(structured={GradeDecision: decision}))

    update = agent(_state(retrieved=[_chunk(0.4, confidence=0.8)]))

    assert update["grade"] == "SUFFICIENT"
    assert update["answer_confidence"] == 0.8  # min supporting source confidence


def test_borderline_with_llm_gap() -> None:
    decision = GradeDecision(grade="GAP", confidence=0.0, reason="off topic")
    agent = GapGraderAgent(ScriptedLLM(structured={GradeDecision: decision}))

    update = agent(_state(retrieved=[_chunk(0.4)]))

    assert update["grade"] == "GAP"
