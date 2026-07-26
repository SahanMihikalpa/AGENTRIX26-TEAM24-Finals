"""API DTOs — the wire contract (snake_case Pydantic, per docs/11).

These translate the JSON-serialisable ``GraphState`` artifacts into the exact
shapes the frontend consumes. Money is rendered as a **number** here (the state
carries it as a precise ``Decimal`` string; Pydantic coerces it on the way out),
matching the doc/11 ``ActionPack`` contract.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.entities import ReportOutcome


class ChatRequest(BaseModel):
    """Body of ``POST /api/chat``. A missing ``session_id`` starts a new thread."""

    message: str
    session_id: str | None = None


class DocumentItemDTO(BaseModel):
    name: str
    mandatory: bool
    notes: str = ""
    source_id: int | None = None


class FeeLineDTO(BaseModel):
    label: str
    amount_lkr: float
    notes: str = ""
    source_id: int | None = None


class OfficeDTO(BaseModel):
    name: str
    address: str
    hours: str = ""
    contact: str = ""
    district: str = ""


class CitationDTO(BaseModel):
    title: str
    last_verified: str
    url: str | None = None
    source_id: int | None = None


class ActionPackDTO(BaseModel):
    """The Action Pack as the frontend consumes it (doc/11 ``ActionPack``)."""

    service_label: str
    district: str | None = None
    documents: list[DocumentItemDTO] = Field(default_factory=list)
    fees: list[FeeLineDTO] = Field(default_factory=list)
    office: OfficeDTO | None = None
    steps: list[str] = Field(default_factory=list)
    estimated_cost_lkr: float = 0.0
    verification: str
    citations: list[CitationDTO] = Field(default_factory=list)
    fallback: bool = False
    fallback_message: str | None = None


# ── feedback (experience reports) ─────────────────────────────────
class ExperienceReportRequest(BaseModel):
    """Body of ``POST /api/experience-reports`` (doc/11 §2, FR-6).

    ``service_id`` / ``session_id`` are optional: when omitted, the service and
    district are resolved from the session's checkpointed state. ``outcome`` is
    validated against :class:`ReportOutcome` (a bad value → 422).
    """

    outcome: ReportOutcome
    session_id: str | None = None
    service_id: int | None = None
    text: str = ""


class ExperienceReportResponse(BaseModel):
    """Acknowledgement returned after a report is filed."""

    id: int
    status: str


# ── moderation queue ──────────────────────────────────────────────
class ModerationItemDTO(BaseModel):
    """One source awaiting review (doc/11 ``ModerationItem``)."""

    source_id: int
    title: str
    url: str | None = None
    source_type: str
    confidence: float
    verification_status: str
    retrieved_date: str
    published_date: str | None = None
    # False for sources found outside the official-domain allow-list. Surfaced so
    # a moderator can see they are about to promote something the government did
    # not publish — the confidence number alone does not say that.
    is_official: bool = True


class ModerationActionResponse(BaseModel):
    """Result of a promote/reject action."""

    ok: bool
