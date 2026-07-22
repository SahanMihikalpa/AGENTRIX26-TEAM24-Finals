"""Helpers for reading a session's checkpointed graph state.

A ``session_id`` is the LangGraph ``thread_id`` (doc/11 §2); the ``SqliteSaver``
persists one :class:`GraphState` per thread. Both the chat resume path and the
experience-report intake (which resolves the service/district from the session)
need to address a thread and read its values, so the two tiny helpers live here.
"""

from __future__ import annotations

from typing import Any


def thread_config(session_id: str) -> dict[str, Any]:
    """The LangGraph config that addresses one session's checkpoint thread."""
    return {"configurable": {"thread_id": session_id}}


def session_values(graph: Any, session_id: str) -> dict[str, Any]:
    """The latest checkpointed state for a session (``{}`` if the thread is empty)."""
    snapshot = graph.get_state(thread_config(session_id))
    return dict(snapshot.values) if snapshot.values else {}
