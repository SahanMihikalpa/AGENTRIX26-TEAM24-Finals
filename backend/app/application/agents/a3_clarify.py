"""A3 · Clarification — the minimal slot-filling interview.

See [docs/agents/a3-clarification.md](../../../docs/agents/a3-clarification.md).
Government processes branch (inheritance vs. sale vs. gift; by district), so a
generic answer is wrong for the individual. A3 asks only the questions needed to
pin a single ``variant_id`` (+ district context), one at a time.

This node is **framework-free**: it computes the next question and writes a
``pending_question`` payload; the actual LangGraph ``interrupt()`` /
``Command(resume=...)`` and the mapping of the user's reply into
``slots[pending_question["slot"]]`` are the supervisor's job in Stage 5. On
re-entry A3 simply reads ``slots`` again, so the interview is naturally resumable.

Options are always grounded in the catalog (variant condition labels); when an
``LLMProvider`` is supplied it only rephrases the question text, otherwise a
template is used (keeps the node deterministic and quota-free).
"""

from __future__ import annotations

import re
from typing import Any

from app.application.agents.schemas import ClarificationQuestion
from app.application.graph.state import GraphState
from app.domain.entities import ServiceVariant
from app.domain.ports.knowledge import KnowledgeStore
from app.domain.ports.llm import LLMProvider

_CONDITION_SLOT = "condition"
_DISTRICT_SLOT = "district"

_SYSTEM = (
    "You phrase one short, friendly clarifying question for a Sri Lankan "
    "government-services assistant. Keep it to a single sentence. Do not add or "
    "remove options — use exactly the options provided."
)


class ClarificationAgent:
    """Drive ``service_id`` → ``variant_id`` (+ district) with minimal questions."""

    def __init__(
        self,
        store: KnowledgeStore,
        llm: LLMProvider | None = None,
        *,
        max_questions: int = 4,
    ) -> None:
        self._store = store
        self._llm = llm
        self._max_questions = max_questions

    def __call__(self, state: GraphState) -> dict[str, Any]:
        service_id = state["service_id"]
        if service_id is None:  # nothing to clarify without a service (defensive)
            return {"pending_question": None}

        slots = dict(state["slots"])
        asked = list(state["asked_slots"])
        variants = self._store.list_variants(service_id)

        variant_id, question = self._resolve_variant(state, variants, slots, asked)
        if question is not None:
            return self._ask(_CONDITION_SLOT, question, asked, slots)

        district_question = self._maybe_ask_district(slots, asked)
        if district_question is not None:
            return self._ask(_DISTRICT_SLOT, district_question, asked, slots)

        # Interview complete: variant pinned (or sensibly defaulted) and context gathered.
        return {"variant_id": variant_id, "pending_question": None, "slots": slots}

    # ── variant resolution ───────────────────────────────────────
    def _resolve_variant(
        self,
        state: GraphState,
        variants: list[ServiceVariant],
        slots: dict[str, Any],
        asked: list[str],
    ) -> tuple[int | None, dict[str, Any] | None]:
        """Return ``(variant_id, question)`` — a question means "ask, don't resolve yet"."""
        if state["variant_id"] is not None:
            return state["variant_id"], None
        if not variants:
            return None, None
        if len(variants) == 1:
            return variants[0].id, None

        answer = self._condition_answer(slots)
        if answer is not None:
            matched = self._match_variant(variants, answer)
            if matched is not None:
                return matched, None

        # The citizen may have already named the variant in their own words
        # ("...the NIC for the first time..."); pin it from the query before asking.
        from_text = self._match_variant_in_text(variants, self._query_text(state))
        if from_text is not None:
            return from_text, None

        # Still ambiguous. Ask once; if we already asked, default to the most
        # common (first) variant and let A6 state the assumption.
        if _CONDITION_SLOT not in asked and len(asked) < self._max_questions:
            options = [v.condition_label for v in variants]
            return None, self._build_question(
                _CONDITION_SLOT,
                "Which of these best describes your situation?",
                options,
            )
        return variants[0].id, None

    @staticmethod
    def _condition_answer(slots: dict[str, Any]) -> str | None:
        """The variant-pinning answer — A1 may have stated it as ``relationship``."""
        for key in (_CONDITION_SLOT, "relationship"):
            value = slots.get(key)
            if value:
                return str(value)
        return None

    @staticmethod
    def _match_variant(variants: list[ServiceVariant], answer: str) -> int | None:
        needle = answer.strip().lower()
        if not needle:
            return None
        for variant in variants:
            label = variant.condition_label.lower()
            if needle == label or needle in label or label in needle:
                return variant.id
        return None

    @staticmethod
    def _query_text(state: GraphState) -> str:
        intent = state["intent"]
        return f"{state['user_query']} {intent.get('normalized_query') or ''}"

    @staticmethod
    def _match_variant_in_text(variants: list[ServiceVariant], text: str) -> int | None:
        """Pin the variant whose label tokens all appear in the citizen's own words.

        Prefers the most specific label (most tokens matched), so "...the NIC for the
        first time..." resolves the ``first-time`` variant without a redundant ask.
        """
        haystack = set(re.findall(r"[a-z0-9]+", text.lower()))
        best_id: int | None = None
        best_len = 0
        for variant in variants:
            tokens = [
                token
                for token in re.findall(r"[a-z0-9]+", variant.condition_label.lower())
                if len(token) >= 3
            ]
            if tokens and len(tokens) > best_len and all(token in haystack for token in tokens):
                best_id, best_len = variant.id, len(tokens)
        return best_id

    # ── district context ─────────────────────────────────────────
    def _maybe_ask_district(
        self, slots: dict[str, Any], asked: list[str]
    ) -> dict[str, Any] | None:
        if slots.get(_DISTRICT_SLOT):
            return None
        if _DISTRICT_SLOT in asked or len(asked) >= self._max_questions:
            return None
        return self._build_question(
            _DISTRICT_SLOT,
            "Which district will you be applying in?",
            options=[],
        )

    # ── question building ────────────────────────────────────────
    def _build_question(
        self, slot: str, base_text: str, options: list[str]
    ) -> dict[str, Any]:
        text = self._phrase(base_text, options)
        return {
            "slot": slot,
            "question": text,
            "options": options,
            "allow_free_text": not options,
        }

    def _phrase(self, base_text: str, options: list[str]) -> str:
        if self._llm is None:
            return base_text
        prompt = (
            f"Base question: {base_text}\n"
            f"Options (use exactly these): {options or 'none — free text answer'}\n"
            "Rephrase the question in one friendly sentence."
        )
        result = self._llm.complete_structured(
            prompt, ClarificationQuestion, system=_SYSTEM
        )
        return result.question or base_text

    @staticmethod
    def _ask(
        slot: str, question: dict[str, Any], asked: list[str], slots: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "pending_question": question,
            "asked_slots": [*asked, slot],
            "slots": slots,
        }
