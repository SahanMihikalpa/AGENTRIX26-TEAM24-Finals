"""B2 · Extract & Curate — raw evidence → validated, provenanced records.

See [docs/agents/b2-extract-curate.md](../../../docs/agents/b2-extract-curate.md).
Each raw document in ``acquisition_buffer`` becomes one schema-constrained
``CuratedExtraction`` (service + variant + requirements + fees + offices) paired
with a ``SOURCE`` stamped ``verification_status = auto_gathered``. Every fact keeps
its provenance: B2 ties the extraction to its source and B3 attaches the resulting
``source_id`` to each row.

``confidence = source authority * extraction certainty`` — local-pool documents
are trusted more than web snippets; the LLM reports its own extraction certainty.
Extractions with no identifiable service are dropped (no usable, mappable fact).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.application.agents.schemas import CuratedExtraction
from app.application.graph.state import GraphState
from app.domain.ports.llm import LLMProvider

_SYSTEM = (
    "You curate Sri Lankan government-service information from a raw document into "
    "structured records. Extract the service (name + a snake_case slug), the "
    "relevant variant/condition, required documents, fees (LKR), and handling "
    "office(s). Use ONLY what the text supports — never invent documents, fees, or "
    "offices. Report your extraction_confidence in [0,1]. If the text is not about "
    "a concrete government service, leave service_name empty."
)

# Source authority feeding ``confidence = authority * extraction_certainty``.
# The local pool is curated government material (most trusted). Web splits by
# provenance: an **official** (allow-listed, e.g. gov.lk) page is authoritative
# enough to clear the serving gate once extracted well, so it can be served
# immediately — labelled "pending verification" until a human confirms it; an
# **unofficial** page (B1's wider fallback) is kept below the gate so it only
# reaches a moderator. Experience reports are a useful but least-authoritative
# real-world signal.
_AUTHORITY: dict[str, float] = {
    "pool": 0.8,
    "web_official": 0.75,
    "web_unofficial": 0.5,
    "experience": 0.4,
}


class ExtractCurateAgent:
    """Turn raw ``acquisition_buffer`` evidence into curated, provenanced records."""

    def __init__(
        self,
        llm: LLMProvider,
        *,
        pool_authority: float = _AUTHORITY["pool"],
        web_official_authority: float = _AUTHORITY["web_official"],
        web_unofficial_authority: float = _AUTHORITY["web_unofficial"],
        experience_authority: float = _AUTHORITY["experience"],
        today: date | None = None,
    ) -> None:
        self._llm = llm
        self._pool_authority = pool_authority
        self._web_official_authority = web_official_authority
        self._web_unofficial_authority = web_unofficial_authority
        self._experience_authority = experience_authority
        self._today = today or date.today()

    def __call__(self, state: GraphState) -> dict[str, Any]:
        curated: list[dict[str, Any]] = []
        for entry in state["acquisition_buffer"]:
            extraction = self._llm.complete_structured(
                self._prompt(entry), CuratedExtraction, system=_SYSTEM
            )
            if not extraction.service_name.strip() or not extraction.service_slug.strip():
                continue  # nothing mappable — drop it (guardrail: no fact without a service)
            curated.append(self._record(entry, extraction))
        return {"curated": curated}

    # ── helpers ──────────────────────────────────────────────────
    def _record(self, entry: dict[str, Any], extraction: CuratedExtraction) -> dict[str, Any]:
        origin = str(entry.get("origin", "web"))
        official = bool(entry.get("official", True))
        confidence = self._confidence(origin, official, extraction.extraction_confidence)
        return {
            "source": {
                "title": entry["title"],
                "url": entry["url"],
                "source_type": entry["source_type"],
                "published_date": entry["published_date"],
                "retrieved_date": self._today.isoformat(),
                "confidence": confidence,
                "verification_status": "auto_gathered",
                "origin": origin,
                # Carried through from B1 so B3 can cap what came from outside the
                # official-domain allow-list. Curation does not judge provenance —
                # it only extracts — so this must survive the hop unchanged.
                "official": bool(entry.get("official", True)),
            },
            "extraction": extraction.model_dump(),
            "text": entry["text"],
        }

    def _confidence(self, origin: str, official: bool, extraction_confidence: float) -> float:
        authority = self._authority_for(origin, official)
        return round(max(0.0, min(1.0, authority * extraction_confidence)), 3)

    def _authority_for(self, origin: str, official: bool) -> float:
        if origin == "pool":
            return self._pool_authority
        if origin == "experience":
            return self._experience_authority
        # Any web origin: an official page is trusted more than a wider-web find.
        return self._web_official_authority if official else self._web_unofficial_authority

    @staticmethod
    def _prompt(entry: dict[str, Any]) -> str:
        title = entry.get("title", "")
        return f"Document title: {title}\n\nDocument text:\n{entry['text']}\n\nCurate it."
