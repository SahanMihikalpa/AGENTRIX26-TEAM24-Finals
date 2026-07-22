"""Pydantic structured-output schemas for the LLM agents.

These live in the **application** layer by design: the ``LLMProvider`` port is
generic over the schema type (``complete_structured(prompt, schema) -> T``), so
the pure domain never imports Pydantic — concrete schemas are supplied here and
validated by the provider's schema-constrained generation (docs/10, Stage 1).

Each schema is the contract for exactly one agent's structured call.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class IntentEntities(BaseModel):
    """Entities A1 may pull out of the raw request (all optional)."""

    district: str | None = None
    relationship: str | None = None
    document_type: str | None = None


class IntentExtraction(BaseModel):
    """A1 · Intake & Intent — the normalised, structured starting point."""

    normalized_query: str
    service_guess: str
    entities: IntentEntities = Field(default_factory=IntentEntities)
    ambiguous: bool = False


class ServiceDisambiguation(BaseModel):
    """A2 · Service Identifier — the LLM picks among close catalog candidates.

    ``service_id`` must be one of the candidate ids offered in the prompt, or
    ``None`` when the model cannot confidently choose (→ ``unknown`` → gap path).
    """

    service_id: int | None = None
    confidence: float = 0.0
    reason: str = ""


class ClarificationQuestion(BaseModel):
    """A3 · Clarification — the next single question to ask the citizen.

    ``options`` are always grounded in the catalog (the variant condition labels);
    the LLM only phrases ``question`` naturally.
    """

    question: str
    options: list[str] = Field(default_factory=list)


class GradeDecision(BaseModel):
    """A5 · Gap Grader — the borderline LLM verdict (Corrective-RAG switch)."""

    grade: Literal["SUFFICIENT", "GAP"]
    confidence: float = 0.0
    reason: str = ""


class ActionSteps(BaseModel):
    """A6 · Action Pack — the human-readable step sequence.

    Only the narrative is LLM-generated; the hard facts (documents, fees, office)
    are assembled deterministically from the store so they stay grounded.
    """

    steps: list[str] = Field(default_factory=list)


# ─────────────── Team 2 · Knowledge Acquisition (Stage 4b) ───────────────


class CuratedRequirement(BaseModel):
    """One document a citizen must bring, extracted by B2."""

    document_name: str
    is_mandatory: bool = True
    notes: str = ""


class CuratedFee(BaseModel):
    """One fee, extracted by B2. Amount is a string to keep money exact (no float)."""

    label: str
    amount_lkr: str = "0"
    notes: str = ""


class CuratedOffice(BaseModel):
    """One office that handles the service, extracted by B2."""

    name: str
    district: str = ""
    address: str = ""
    hours: str = ""
    contact: str = ""


class CuratedExtraction(BaseModel):
    """B2 · Extract & Curate — canonical records pulled from one raw document.

    Schema-constrained extraction with mandatory provenance: B2 ties this to the
    document's source, and B3 attaches the resulting ``source_id`` to every row.
    ``service_name``/``service_slug`` empty ⇒ nothing usable was found (B2 drops it).
    """

    service_name: str = ""
    service_slug: str = ""
    category: str = ""
    description: str = ""
    condition_label: str = "standard"
    requirements: list[CuratedRequirement] = Field(default_factory=list)
    fees: list[CuratedFee] = Field(default_factory=list)
    offices: list[CuratedOffice] = Field(default_factory=list)
    district: str = ""
    district_notes: str = ""
    extraction_confidence: float = 0.5
