"""A5 · Gap Grader — decide whether retrieved evidence is good enough to answer.

See [docs/agents/a5-gap-grader.md](../../../docs/agents/a5-gap-grader.md).
This is the **Corrective-RAG switch** that drives the self-expanding loop
(docs/03): emit ``SUFFICIENT`` or ``GAP``, plus ``answer_confidence`` (the min
confidence of the supporting facts) which A6 uses for the serving gate (AD-8).

Two-stage grading keeps the free-tier cost down:

1. Cheap score/coverage threshold handles the clear majority.
2. A short LLM yes/no check is spent **only** on the borderline band — and only
   if an ``LLMProvider`` is supplied; without one we bias to ``GAP`` (better to
   research than to answer wrong).

An ``unknown`` service (A2) or empty retrieval is an immediate ``GAP``.
"""

from __future__ import annotations

from typing import Any

from app.application.agents.schemas import GradeDecision
from app.application.graph.state import GraphState
from app.domain.entities import Grade
from app.domain.ports.llm import LLMProvider

_SYSTEM = (
    "You judge whether retrieved context is sufficient to answer a citizen's "
    "government-services question (required documents, fees, and office). Answer "
    "SUFFICIENT only if the context plainly covers the need; otherwise GAP. When "
    "unsure, prefer GAP."
)


class GapGraderAgent:
    """Grade ``retrieved`` → ``SUFFICIENT`` | ``GAP`` (+ serving confidence)."""

    def __init__(
        self,
        llm: LLMProvider | None = None,
        *,
        sufficient_above: float = 0.5,
        gap_below: float = 0.3,
    ) -> None:
        self._llm = llm
        self._sufficient_above = sufficient_above
        self._gap_below = gap_below

    def __call__(self, state: GraphState) -> dict[str, Any]:
        if state["service_unknown"]:
            return self._gap("service is not in the catalog")

        retrieved = state["retrieved"]
        if not retrieved:
            return self._gap("no evidence retrieved")

        top_score = max(float(chunk["score"]) for chunk in retrieved)
        confidence = self._supporting_confidence(retrieved)

        if top_score >= self._sufficient_above:
            return self._sufficient("retrieval score above threshold", confidence)
        if top_score < self._gap_below:
            return self._gap("retrieval score below threshold")

        # Borderline band → spend a cheap LLM check, or bias to GAP without one.
        if self._llm is None:
            return self._gap("borderline retrieval, no verifier available")
        return self._llm_grade(state, confidence)

    # ── helpers ──────────────────────────────────────────────────
    def _llm_grade(self, state: GraphState, confidence: float) -> dict[str, Any]:
        decision = self._llm.complete_structured(  # type: ignore[union-attr]
            self._prompt(state),
            GradeDecision,
            system=_SYSTEM,
        )
        if decision.grade == Grade.SUFFICIENT:
            return self._sufficient(decision.reason or "verified by LLM", confidence)
        return self._gap(decision.reason or "judged insufficient by LLM")

    def _supporting_confidence(self, retrieved: list[dict[str, Any]]) -> float:
        """Min source confidence among plausibly-supporting chunks (the gate input)."""
        supporting = [
            float(chunk["confidence"])
            for chunk in retrieved
            if float(chunk["score"]) >= self._gap_below
        ]
        return min(supporting) if supporting else 0.0

    @staticmethod
    def _sufficient(reason: str, confidence: float) -> dict[str, Any]:
        return {
            "grade": Grade.SUFFICIENT.value,
            "grade_reason": reason,
            "answer_confidence": confidence,
        }

    @staticmethod
    def _gap(reason: str) -> dict[str, Any]:
        return {
            "grade": Grade.GAP.value,
            "grade_reason": reason,
            "answer_confidence": 0.0,
        }

    @staticmethod
    def _prompt(state: GraphState) -> str:
        intent = state["intent"]
        query = str(intent.get("normalized_query") or state["user_query"])
        context = "\n---\n".join(
            str(chunk["content"]) for chunk in state["retrieved"]
        )
        return f"Question: {query}\n\nRetrieved context:\n{context}\n\nGrade it."
