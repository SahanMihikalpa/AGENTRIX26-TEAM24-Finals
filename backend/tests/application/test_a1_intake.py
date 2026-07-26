"""A1 · Intake & Intent."""

from __future__ import annotations

from app.application.agents.a1_intake import IntakeIntentAgent
from app.application.agents.schemas import IntentEntities, IntentExtraction
from app.application.graph.state import new_state
from tests.application.conftest import ScriptedLLM


def test_writes_intent_and_seeds_known_slots() -> None:
    intent = IntentExtraction(
        normalized_query="transfer inherited land deed",
        service_guess="land_deed_transfer",
        entities=IntentEntities(district="Galle", relationship="inheritance"),
        ambiguous=False,
    )
    agent = IntakeIntentAgent(ScriptedLLM(structured={IntentExtraction: intent}))

    update = agent(new_state("s1", "I need to sort out my dad's land in Galle"))

    assert update["intent"]["service_guess"] == "land_deed_transfer"
    # entities the citizen already stated pre-fill the interview slots (A3 skips them)
    assert update["slots"] == {"district": "Galle", "relationship": "inheritance"}


def test_leaves_unstated_slots_empty() -> None:
    intent = IntentExtraction(
        normalized_query="register a business name",
        service_guess="business_name_registration",
    )
    agent = IntakeIntentAgent(ScriptedLLM(structured={IntentExtraction: intent}))

    update = agent(new_state("s2", "how do I register a business"))

    assert update["slots"] == {}
    assert update["intent"]["ambiguous"] is False


# ── conversation history (multi-turn follow-ups) ─────────────────
class CapturingLLM(ScriptedLLM):
    """Records the prompts so the history wiring can be asserted on."""

    def __init__(self, intent: IntentExtraction) -> None:
        super().__init__(structured={IntentExtraction: intent})
        self.prompts: list[str] = []

    def complete_structured(
        self, prompt: str, schema: type, *, system: str | None = None, temperature: float = 0.0
    ) -> object:
        self.prompts.append(prompt)
        return super().complete_structured(prompt, schema, system=system, temperature=temperature)


def _intent() -> IntentExtraction:
    return IntentExtraction(
        normalized_query="land deed transfer in Kandy",
        service_guess="land_deed_transfer",
        entities=IntentEntities(district="Kandy"),
        ambiguous=False,
    )


def test_a_first_turn_prompt_carries_no_transcript() -> None:
    llm = CapturingLLM(_intent())

    IntakeIntentAgent(llm)(new_state("s1", "transfer my land"))

    assert "Conversation so far" not in llm.prompts[0]


def test_a_follow_up_is_resolved_against_the_conversation() -> None:
    """"what about Kandy?" means nothing alone — A1 is what makes it standalone."""
    llm = CapturingLLM(_intent())
    state = new_state("s1", "what about Kandy?")
    state["history"] = [
        {"role": "user", "text": "transfer my late father's land to my name"},
        {"role": "assistant", "text": "Answered about: Land Deed Transfer (sale-transfer)"},
    ]

    update = IntakeIntentAgent(llm)(state)

    prompt = llm.prompts[0]
    assert "Conversation so far" in prompt
    assert "transfer my late father's land to my name" in prompt
    assert "Land Deed Transfer (sale-transfer)" in prompt
    assert "latest turn" in prompt
    assert update["slots"]["district"] == "Kandy"
