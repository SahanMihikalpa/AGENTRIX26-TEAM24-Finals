"""Agent nodes — framework-free callables ``(GraphState) -> dict`` over the ports.

Team 1 (Answering) A1-A6 and Team 2 (Acquisition) B1-B4 land in Stage 4; the
LangGraph wiring that registers these as nodes is Stage 5.
"""

from app.application.agents.a1_intake import IntakeIntentAgent
from app.application.agents.a2_identify import ServiceIdentifierAgent
from app.application.agents.a3_clarify import ClarificationAgent
from app.application.agents.a4_retrieval import RetrievalAgent
from app.application.agents.a5_grader import GapGraderAgent
from app.application.agents.a6_action_pack import ActionPackAgent
from app.application.agents.b1_research import ResearchAgent
from app.application.agents.b2_curate import ExtractCurateAgent
from app.application.agents.b3_kb_updater import KBUpdaterAgent
from app.application.agents.b4_moderation import ModerationGateAgent

__all__ = [
    "ActionPackAgent",
    "ClarificationAgent",
    "ExtractCurateAgent",
    "GapGraderAgent",
    "IntakeIntentAgent",
    "KBUpdaterAgent",
    "ModerationGateAgent",
    "ResearchAgent",
    "RetrievalAgent",
    "ServiceIdentifierAgent",
]
