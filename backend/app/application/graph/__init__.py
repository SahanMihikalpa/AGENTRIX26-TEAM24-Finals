"""Graph layer — the ``GraphState`` blackboard and the LangGraph wiring.

Stage 4 defined the state + framework-free agents; Stage 5 (``builder``) assembles
them into the supervised ``StateGraph`` with the bounded gap loop, A3 interrupt, and
an injected checkpointer.

Only the lightweight, agent-free pieces (``GraphState``, ``new_state``,
``GraphDependencies``) are re-exported here. ``build_graph`` is imported directly
from ``app.application.graph.builder`` to avoid an import cycle: the agents depend
on ``GraphState`` (this package), and the builder depends on the agents.
"""

from app.application.graph.dependencies import GraphDependencies
from app.application.graph.state import GraphState, new_state

__all__ = ["GraphDependencies", "GraphState", "new_state"]
