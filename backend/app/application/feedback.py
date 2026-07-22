"""Experience-report intake — the *second* entrypoint into the B2→B3 pipeline.

See [docs/03 · self-expanding RAG](../../../docs/03-self-expanding-rag.md) (§"Same
pipeline, second source"). A citizen's post-visit report ("they also asked for X")
is real-world signal, so it flows through the **same** curation + KB-update agents
the gap loop uses — not only web research grows the knowledge base.

Contract: the report is **always persisted** (a feedback record, ``status=pending``);
feeding it through B2→B3 is **best-effort** — if extraction/embedding fails, or the
text yields no mappable service, the report is still saved and the call still
succeeds. Anything B3 writes lands as ``auto_gathered`` and surfaces in the
moderation queue (B4 / Stage 6b), so citizen-sourced facts stay clearly provisional
until a human promotes them.

This is an application **use case**: it orchestrates the ports + the B2/B3 agents and
imports no framework (stdlib ``logging`` only), keeping the hexagonal boundary clean.
"""

from __future__ import annotations

import logging
from typing import Any

from app.application.agents.b2_curate import ExtractCurateAgent
from app.application.agents.b3_kb_updater import KBUpdaterAgent
from app.application.graph.state import new_state
from app.domain.entities import ExperienceReport, SourceType
from app.domain.ports.embeddings import EmbeddingProvider
from app.domain.ports.knowledge import KnowledgeStore
from app.domain.ports.llm import LLMProvider

_log = logging.getLogger(__name__)


class ExperienceReportIntake:
    """Persist an experience report, then best-effort ingest it via B2→B3."""

    def __init__(
        self,
        store: KnowledgeStore,
        llm: LLMProvider,
        embedder: EmbeddingProvider,
    ) -> None:
        self._store = store
        self._curator = ExtractCurateAgent(llm)
        self._updater = KBUpdaterAgent(store, embedder)

    def submit(self, report: ExperienceReport) -> ExperienceReport:
        """Save the report (always) and try to grow the KB from it (best-effort)."""
        saved = self._store.add_experience_report(report)
        try:
            self._ingest(saved)
        except Exception:  # a flaky LLM/embed must never lose the citizen's report
            _log.exception("experience-report ingestion failed (report saved, id=%s)", saved.id)
        return saved

    # ── B2 → B3 over a single report ─────────────────────────────
    def _ingest(self, report: ExperienceReport) -> None:
        if not report.report_text.strip():
            return  # nothing to extract
        state = new_state(
            session_id=f"experience-{report.id}", user_query=report.report_text
        )
        state["acquisition_buffer"] = [self._buffer_entry(report)]
        state["curated"] = self._curator(state).get("curated", [])  # B2
        if state["curated"]:
            self._updater(state)  # B3 → embed + upsert (auto_gathered → moderation queue)

    @staticmethod
    def _buffer_entry(report: ExperienceReport) -> dict[str, Any]:
        """Shape the report as a raw B1-style evidence entry for B2 to curate."""
        return {
            "text": report.report_text,
            "title": f"Citizen experience report ({report.reported_outcome.value})",
            "url": None,
            "source_type": SourceType.EXPERIENCE.value,
            "published_date": None,
            "origin": "experience",
        }
