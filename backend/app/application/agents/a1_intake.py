"""A1 · Intake & Intent — normalise the raw request into structured intent.

See [docs/agents/a1-intake-intent.md](../../../docs/agents/a1-intake-intent.md).
One structured LLM call turns messy free text into ``{normalized_query,
service_guess, entities, ambiguous}`` and seeds any slots the citizen already
stated (district / relationship), which A3 can then skip asking.
"""

from __future__ import annotations

from typing import Any

from app.application.agents.schemas import IntentExtraction
from app.application.graph.state import GraphState
from app.domain.ports.llm import LLMProvider

_SYSTEM = (
    "You are the intake step of a Sri Lankan government-services assistant. "
    "Read the citizen's request and extract a clean, structured intent. "
    "Normalise the query into a concise canonical phrase, give a coarse "
    "snake_case service_guess (e.g. land_deed_transfer), and pull out only "
    "entities the user actually stated. Never invent facts. Set ambiguous=true "
    "if the request could reasonably map to more than one government service. "
    "The system is English-only.\n\n"
    "Earlier turns may be supplied. A follow-up is often meaningless on its own "
    "(\"what about Kandy?\", \"and if it's a gift instead?\") — resolve it against "
    "the conversation so normalized_query stands alone without it. If the citizen "
    "has clearly moved to a different service, treat the new request on its own "
    "terms and do not carry the old subject over."
)


class IntakeIntentAgent:
    """LLM (structured) agent that produces the intent and seeds known slots."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def __call__(self, state: GraphState) -> dict[str, Any]:
        result = self._llm.complete_structured(
            self._prompt(state["user_query"], state.get("history") or []),
            IntentExtraction,
            system=_SYSTEM,
        )

        # A1 partially fills slots from entities the citizen already mentioned,
        # so A3 only has to ask for what is still missing.
        slots = dict(state["slots"])
        if result.entities.district:
            slots["district"] = result.entities.district
        if result.entities.relationship:
            slots["relationship"] = result.entities.relationship

        return {"intent": result.model_dump(), "slots": slots}

    @staticmethod
    def _prompt(user_query: str, history: list[dict[str, str]]) -> str:
        if not history:
            return f"Citizen request:\n{user_query}\n\nExtract the structured intent."
        transcript = "\n".join(
            f"{turn.get('role', 'user')}: {turn.get('text', '')}" for turn in history
        )
        return (
            f"Conversation so far:\n{transcript}\n\n"
            f"Citizen request (latest turn):\n{user_query}\n\n"
            "Extract the structured intent for the latest turn, resolved against "
            "the conversation."
        )
