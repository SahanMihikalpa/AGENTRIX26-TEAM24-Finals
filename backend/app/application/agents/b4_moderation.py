"""B4 · Moderation Gate — keep auto-gathered knowledge usable but provisional.

See [docs/agents/b4-moderation.md](../../../docs/agents/b4-moderation.md).
Policy is **serve-but-label, never block**: newly acquired (``auto_gathered``)
records stay retrievable and answerable, but are queued for a human to promote to
``verified``. A6 already shows the "pending verification" label; B4 surfaces the
items that need review.

MVP scope (per the doc): this node is **rules-only** — it appends queue entries to
``moderation_queue`` (deduped by url+title). The actual promote/reject transitions
are the Stage 6 moderation API + a store status update; the LangGraph
human-in-the-loop console is roadmap.
"""

from __future__ import annotations

from typing import Any

from app.application.graph.state import GraphState


class ModerationGateAgent:
    """Queue non-verified acquired records for human review (no blocking)."""

    def __init__(self, *, confidence_threshold: float = 0.6) -> None:
        self._confidence_threshold = confidence_threshold

    def __call__(self, state: GraphState) -> dict[str, Any]:
        queue = list(state["moderation_queue"])
        seen = {(entry.get("url"), entry.get("source_title")) for entry in queue}

        for record in state["curated"]:
            src = record["source"]
            if src.get("verification_status") == "verified":
                continue  # verified data never needs moderation
            key = (src.get("url"), src.get("title"))
            if key in seen:
                continue  # dedup across loops
            seen.add(key)
            queue.append(self._entry(record, src))

        return {"moderation_queue": queue}

    def _entry(self, record: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
        confidence = float(src.get("confidence", 0.0))
        return {
            "source_title": src.get("title"),
            "url": src.get("url"),
            "service_name": record["extraction"].get("service_name"),
            "confidence": confidence,
            "verification_status": src.get("verification_status"),
            "status": "pending",
            # web-origin or low-confidence items are the ones a moderator should see first
            "needs_review": confidence < self._confidence_threshold
            or src.get("origin") == "web",
        }
