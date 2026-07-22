"""Domain entities, value objects, and enums — the pure core.

PURE LAYER: this module (and everything under ``app.domain``) imports only the
Python standard library. No FastAPI, Pydantic, LangChain, Chroma, or SQL — the
dependency rule (AD-9) points inward, and ``tests/domain/test_purity.py``
enforces it automatically.

Modeled to the ER in ``docs/05-data-model.md``. Conventions:

* ``@dataclass(frozen=True, slots=True)`` everywhere → immutable, hashable value
  semantics that are safe to pass through the LangGraph ``GraphState``.
* Money is :class:`decimal.Decimal` (never ``float``).
* Database-assigned identifiers are ``int | None`` (``None`` until persisted).
* Collections are tuples (immutable).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

# ───────────────────────────── Enums ─────────────────────────────


class Grade(StrEnum):
    """A5 gap-grader verdict — the Corrective-RAG switch."""

    SUFFICIENT = "SUFFICIENT"
    GAP = "GAP"


class VerificationStatus(StrEnum):
    """Trust label carried by every :class:`Source` (docs/05 confidence gate).

    ``REJECTED`` is set by a moderator (B4 / Stage 6b): the source is quarantined —
    excluded from the moderation queue and de-indexed so it is neither served nor
    re-ingested (the row itself stays for dedup). A delta from the ER's three-value
    enum, logged in docs/05 + docs/10.
    """

    VERIFIED = "verified"
    AUTO_GATHERED = "auto_gathered"
    PENDING = "pending"
    REJECTED = "rejected"


class SourceType(StrEnum):
    GAZETTE = "gazette"
    CIRCULAR = "circular"
    PORTAL = "portal"
    EXPERIENCE = "experience"


class OfficeType(StrEnum):
    DS = "DS"  # Divisional Secretariat
    PRADESHIYA = "Pradeshiya"
    DRP = "DRP"  # District Registrar of Persons
    OTHER = "other"


class ReportOutcome(StrEnum):
    MATCHED = "matched"
    EXTRA_DOC = "extra_doc"
    WRONG_OFFICE = "wrong_office"
    OTHER = "other"


class ReportStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ActionPackVerification(StrEnum):
    """The label A6 stamps on the Action Pack (see ``docs/agents/a6-...``)."""

    VERIFIED = "verified"
    NEWLY_GATHERED_PENDING_VERIFICATION = "newly_gathered_pending_verification"


class ServiceCategory(StrEnum):
    """Controlled vocabulary for ``Service.category`` — UI grouping + consistency.

    Verified seed data is validated against this list (the seeder rejects an
    unknown category). ``Service.category`` itself stays a plain ``str`` so the
    self-expanding path is never blocked by an out-of-vocabulary value that B3
    may auto-gather; the members here are the canonical labels stored in SQLite
    and shown in the UI. Tune the list freely — it is the single source of truth.
    """

    CIVIL_REGISTRATION = "Civil Registration & Identity"
    LAND_PROPERTY = "Land & Property"
    BUSINESS_COMMERCE = "Business & Commerce"
    MOTOR_TRANSPORT = "Motor Traffic & Transport"
    PASSPORT_IMMIGRATION = "Passport & Immigration"
    TAXATION_REVENUE = "Taxation & Revenue"
    EDUCATION = "Education & Examinations"
    HEALTH_WELFARE = "Health & Welfare"
    SOCIAL_SERVICES = "Social Services & Pensions"
    POLICE_LEGAL = "Police & Legal"
    UTILITIES = "Utilities"
    OTHER = "Other"


# ─────────────────────────── Catalog ───────────────────────────


@dataclass(frozen=True, slots=True)
class Service:
    """A government service the system can answer for (e.g. land deed transfer)."""

    name_en: str
    slug: str
    category: str
    description: str
    id: int | None = None


@dataclass(frozen=True, slots=True)
class ServiceVariant:
    """A branch of a service (e.g. inheritance | sale | gift) — what A3 pins down."""

    service_id: int
    condition_label: str
    description: str
    id: int | None = None


@dataclass(frozen=True, slots=True)
class Requirement:
    """A document the citizen must bring for a given variant."""

    variant_id: int
    source_id: int
    document_name: str
    is_mandatory: bool
    notes: str = ""
    id: int | None = None


@dataclass(frozen=True, slots=True)
class Fee:
    """A monetary charge for a variant (amount in LKR, never a float)."""

    variant_id: int
    source_id: int
    label: str
    amount_lkr: Decimal
    notes: str = ""
    id: int | None = None


@dataclass(frozen=True, slots=True)
class Office:
    """A physical office that handles a service. (ER ``type`` → ``office_type``.)"""

    name: str
    office_type: OfficeType
    district: str
    address: str
    hours: str
    contact: str
    geo_lat: float | None = None
    geo_lng: float | None = None
    id: int | None = None


@dataclass(frozen=True, slots=True)
class DistrictVariation:
    """A district-specific deviation in a service's requirements."""

    service_id: int
    source_id: int
    district: str
    notes: str = ""
    id: int | None = None


@dataclass(frozen=True, slots=True)
class ServiceOffice:
    """Link row: which offices handle which services."""

    service_id: int
    office_id: int


# ───────────────────────── Provenance ─────────────────────────


@dataclass(frozen=True, slots=True)
class Source:
    """Evidence behind a fact — every fact cites one (docs/05 confidence gate).

    ``url`` is optional because local source-pool documents are referenced by
    path and experience reports have no URL.
    """

    title: str
    source_type: SourceType
    retrieved_date: date
    confidence: float
    verification_status: VerificationStatus
    url: str | None = None
    published_date: date | None = None
    id: int | None = None


@dataclass(frozen=True, slots=True)
class KBChunk:
    """A chunk of source text stored for vector retrieval (links to its vector)."""

    source_id: int
    service_id: int | None
    content: str
    chunk_index: int
    vector_ref: str | None = None
    id: int | None = None


# ─────────────────── Retrieval value object (A4) ───────────────────


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A scored chunk returned by the Retriever, with its provenance attached."""

    content: str
    score: float
    source: Source
    service_id: int | None
    chunk_index: int


# ─────────────────── Action Pack (A6 artifact) ───────────────────


@dataclass(frozen=True, slots=True)
class DocumentItem:
    name: str
    mandatory: bool
    source_id: int | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class FeeLine:
    label: str
    amount_lkr: Decimal
    source_id: int | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class ActionPackOffice:
    name: str
    address: str
    hours: str
    contact: str = ""
    district: str = ""


@dataclass(frozen=True, slots=True)
class Citation:
    title: str
    url: str | None
    last_verified: date
    source_id: int | None = None


@dataclass(frozen=True, slots=True)
class ActionPack:
    """The grounded, cited, printable answer A6 produces for the citizen."""

    service_label: str
    district: str | None
    documents: tuple[DocumentItem, ...]
    fees: tuple[FeeLine, ...]
    office: ActionPackOffice | None
    steps: tuple[str, ...]
    estimated_cost_lkr: Decimal
    verification: ActionPackVerification
    citations: tuple[Citation, ...]
    fallback: bool = False
    fallback_message: str | None = None


# ───────────────────────── Feedback ─────────────────────────


@dataclass(frozen=True, slots=True)
class ExperienceReport:
    """A citizen's post-visit report — feeds the B2→B3 pipeline (docs/03).

    ``service_id`` is optional (nullable FK in the ER): a report may be filed
    without a resolved service, or the API may resolve it from the session.
    """

    service_id: int | None
    district: str
    report_text: str
    reported_outcome: ReportOutcome
    status: ReportStatus
    created_at: datetime
    id: int | None = None


# ───────────────────────── Session ─────────────────────────


@dataclass(frozen=True, slots=True)
class Session:
    """A chat session (= LangGraph ``thread_id``)."""

    district: str | None
    created_at: datetime
    id: int | None = None


@dataclass(frozen=True, slots=True)
class SessionMessage:
    session_id: int
    role: MessageRole
    content: str
    created_at: datetime
    id: int | None = None


@dataclass(frozen=True, slots=True)
class StoredChecklist:
    """A persisted Action Pack produced within a session (ER ``CHECKLIST``)."""

    session_id: int
    variant_id: int
    action_pack: ActionPack
    created_at: datetime
    id: int | None = None
