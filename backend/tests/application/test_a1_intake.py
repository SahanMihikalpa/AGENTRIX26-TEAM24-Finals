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
