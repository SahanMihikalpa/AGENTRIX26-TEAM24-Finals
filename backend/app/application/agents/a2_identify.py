"""A2 · Service Identifier — resolve the intent to one catalog ``service_id``.

See [docs/agents/a2-service-identifier.md](../../../docs/agents/a2-service-identifier.md).
Retrieval-assisted classification: match the normalised query against the
**catalog** (never let the LLM invent a service id). A unique candidate is
accepted directly; when several candidates are close, a short LLM disambiguation
call chooses among *their* ids. No confident match → ``service_unknown`` →
the gap path handles it (which is exactly how new services get acquired).

Delta vs. docs (logged in docs/10): catalog matching is **lexical**
(``find_services``) + LLM disambiguation for the MVP; full vector service-matching
remains a noted future enhancement.
"""

from __future__ import annotations

from typing import Any

from app.application.agents.schemas import ServiceDisambiguation
from app.application.graph.state import GraphState
from app.domain.entities import Service, ServiceCoverage
from app.domain.ports.knowledge import KnowledgeStore
from app.domain.ports.llm import LLMProvider


def _coverage_note(coverage: ServiceCoverage) -> str:
    """Render coverage as something an LLM can weigh, not a raw tuple."""
    if not coverage.is_answerable:
        return "no documented requirements — cannot produce a checklist"
    parts = [f"{coverage.requirements} documented requirement(s)"]
    if coverage.fees:
        parts.append(f"{coverage.fees} fee(s)")
    if coverage.offices:
        parts.append(f"{coverage.offices} office(s)")
    return ", ".join(parts)

_SYSTEM = (
    "You disambiguate which government service a citizen means. You are given a "
    "request and a short list of candidate services (id + name + description), each "
    "annotated with how much documented information the knowledge base holds for it. "
    "Choose the single best matching id, or return service_id=null if none "
    "clearly fits. Only ever return an id from the candidate list.\n\n"
    "When two candidates both plausibly cover the request — typically a broad "
    "service and a narrower entry whose name repeats the citizen's words — choose "
    "the one with documented requirements and fees. The narrower entry is usually a "
    "duplicate of a case the broader service already covers in detail, and picking "
    "it means the citizen gets no checklist at all. Only prefer a candidate with no "
    "documented information when it is the sole one that actually matches."
)


class ServiceIdentifierAgent:
    """Map intent → one ``service_id`` (or ``unknown``) against the catalog."""

    def __init__(
        self,
        store: KnowledgeStore,
        llm: LLMProvider | None = None,
        *,
        candidate_limit: int = 5,
        min_confidence: float = 0.5,
        confidence_threshold: float = 0.6,
    ) -> None:
        self._store = store
        self._llm = llm
        # Mirrors A6's AD-8 gate: facts below this are not counted as coverage,
        # because A6 would refuse to serve them and the citizen would get the
        # fallback from a service that looked well-documented here.
        self._confidence_threshold = confidence_threshold
        self._candidate_limit = candidate_limit
        self._min_confidence = min_confidence

    def __call__(self, state: GraphState) -> dict[str, Any]:
        query = self._query(state)
        candidates = self._store.find_services(query, limit=self._candidate_limit)

        if not candidates:
            return self._unknown()

        if len(candidates) == 1:
            return self._resolved(candidates[0])

        # Several candidates: let the LLM choose among their ids if available,
        # otherwise fall back to the first (lexically best) match.
        if self._llm is None:
            return self._resolved(candidates[0])

        coverage = self._store.get_service_coverage(
            [c.id for c in candidates if c.id is not None],
            min_source_confidence=self._confidence_threshold,
        )
        decision = self._llm.complete_structured(
            self._disambiguation_prompt(query, candidates, coverage),
            ServiceDisambiguation,
            system=_SYSTEM,
        )
        chosen = self._validate_choice(decision, candidates)
        if chosen is None or decision.confidence < self._min_confidence:
            return self._unknown()
        return self._resolved(chosen)

    # ── helpers ──────────────────────────────────────────────────
    @staticmethod
    def _query(state: GraphState) -> str:
        intent = state["intent"]
        return str(intent.get("normalized_query") or state["user_query"])

    @staticmethod
    def _validate_choice(
        decision: ServiceDisambiguation, candidates: list[Service]
    ) -> Service | None:
        if decision.service_id is None:
            return None
        return next((c for c in candidates if c.id == decision.service_id), None)

    @staticmethod
    def _resolved(service: Service) -> dict[str, Any]:
        return {"service_id": service.id, "service_unknown": False}

    @staticmethod
    def _unknown() -> dict[str, Any]:
        return {"service_id": None, "service_unknown": True}

    @staticmethod
    def _disambiguation_prompt(
        query: str, candidates: list[Service], coverage: dict[int, ServiceCoverage]
    ) -> str:
        lines = [
            f"- id={c.id}: {c.name_en} — {c.description}".rstrip(" —")
            + f" [{_coverage_note(coverage.get(c.id or -1, ServiceCoverage()))}]"
            for c in candidates
        ]
        catalog = "\n".join(lines)
        return f"Citizen request: {query}\n\nCandidate services:\n{catalog}"
