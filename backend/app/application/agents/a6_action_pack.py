"""A6 · Action-Pack Generator — compose the grounded, cited, printable answer.

See [docs/agents/a6-action-pack-generator.md](../../../docs/agents/a6-action-pack-generator.md)
and the [confidence serving gate](../../../docs/05-data-model.md#confidence-serving-gate).

Order of operations (the gate is first, deliberately — a *label* does not stop a
*bad* answer, AD-8 / QA-1):

1. **Confidence gate.** If we are in fallback mode (``grade != SUFFICIENT``) or the
   supporting facts are ``auto_gathered`` with ``answer_confidence < τ``, **do not
   render** a pack — return the graceful fallback (the office to contact directly).
2. Otherwise assemble the pack. The hard facts (documents, fees, office) are read
   **deterministically from the store** for the resolved variant/district, so every
   line traces to a real row (no LLM invention, and the gap loop's fresh rows are
   picked up). The ``LLMProvider`` — when supplied — only sequences the
   human-readable ``steps``.

Delta vs. docs (logged in docs/10): the doc shows the LLM filling the whole
ActionPack; we instead assemble facts deterministically and let the LLM phrase only
the steps — a stronger groundedness guarantee. The cost/transport heuristic (cost
tool) is deferred to Stage 7; ``estimated_cost_lkr`` is currently the sum of fees.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from app.application.agents.schemas import ActionSteps
from app.application.graph.serialization import action_pack_to_state
from app.application.graph.state import GraphState
from app.domain.entities import (
    ActionPack,
    ActionPackOffice,
    ActionPackVerification,
    Citation,
    DocumentItem,
    FeeLine,
    Grade,
    Office,
    Service,
    ServiceVariant,
    Source,
    VerificationStatus,
)
from app.domain.ports.knowledge import KnowledgeStore
from app.domain.ports.llm import LLMProvider

_SYSTEM = (
    "You write the step-by-step instructions for a citizen completing a Sri "
    "Lankan government process. Use ONLY the documents, fees, and office given. "
    "Produce a short, ordered list of clear, practical steps. Do not invent "
    "documents, fees, amounts, or offices."
)

_FALLBACK_GAP = "We couldn't find verified information for this exact request yet."
_FALLBACK_LOW_CONFIDENCE = (
    "We found a related source but couldn't verify it with enough confidence to "
    "give you a checklist."
)
# Contact guidance + first step adapt to whether we actually have an office to show.
_CONTACT_OFFICE = " Please contact the office below to confirm the requirements directly."
_CONTACT_GENERIC = (
    " Please contact the relevant government department to confirm the requirements directly."
)
_STEP_OFFICE = "Contact the office below to confirm the exact requirements."
_STEP_GENERIC = "Contact the relevant government department to confirm the exact requirements."


@dataclass(frozen=True, slots=True)
class _Facts:
    """Everything the pack is made of, read once so the gate can judge it."""

    service: Service | None
    variant: ServiceVariant | None
    documents: list[DocumentItem]
    fees: list[FeeLine]
    office: ActionPackOffice | None
    backing_sources: list[Source]
    variants: list[ServiceVariant] = field(default_factory=list)


class ActionPackAgent:
    """Generate the Action Pack (or the confidence-gated fallback)."""

    def __init__(
        self,
        store: KnowledgeStore,
        llm: LLMProvider | None = None,
        *,
        confidence_threshold: float = 0.6,
    ) -> None:
        self._store = store
        self._llm = llm
        self._confidence_threshold = confidence_threshold

    def __call__(self, state: GraphState) -> dict[str, Any]:
        # The facts are assembled first because the gate is a judgement *about
        # them*. This costs only store reads — the LLM is still never called for a
        # pack that will not be served, which is what "the gate is first" protects.
        facts = self._assemble_facts(state)
        gate_message = self._gate(state, facts.backing_sources)
        if gate_message is not None:
            pack = self._fallback_pack(state, gate_message)
        else:
            pack = self._build_pack(state, facts)

        answer = action_pack_to_state(pack)
        return {"answer": answer, "citations": answer["citations"]}

    # ── fact assembly (deterministic, grounded) ──────────────────
    def _assemble_facts(self, state: GraphState) -> _Facts:
        """Read the rows the pack would render, plus the sources behind them."""
        service_id = state["service_id"]
        service = self._store.get_service(service_id) if service_id is not None else None
        if service is None or service_id is None:
            return _Facts(None, None, [], [], None, [])

        variants = self._store.list_variants(service_id)
        variant = self._pick_variant(state["variant_id"], variants)
        documents = self._documents(variant)
        fees = self._fees(variant)
        office = self._office(service_id, state["slots"].get("district"))

        source_ids = [
            source_id
            for source_id in (
                *(doc.source_id for doc in documents),
                *(fee.source_id for fee in fees),
            )
            if source_id is not None
        ]
        sources = self._store.get_sources(source_ids)
        # Preserve first-seen order so citations read in the order the facts do.
        backing: list[Source] = []
        seen: set[int] = set()
        for source_id in source_ids:
            source = sources.get(source_id)
            if source is not None and source_id not in seen:
                seen.add(source_id)
                backing.append(source)
        return _Facts(service, variant, documents, fees, office, backing, variants)

    # ── confidence gate (AD-8) ───────────────────────────────────
    def _gate(self, state: GraphState, backing: list[Source]) -> str | None:
        """Return a fallback message if the pack must NOT be rendered, else ``None``.

        The gate judges the pack by **the sources behind the rows it is about to
        render**, not by whatever A4 happened to retrieve. Those are different
        things: A6 assembles documents and fees deterministically from the store,
        each carrying its own ``source_id``, while retrieval returns the nearest
        chunks — which may include crawled text that contributed nothing to the
        answer. Judging on retrieval meant one stray low-confidence chunk could
        suppress a checklist built entirely from verified rows.

        This is not a loosening. Nothing unverified is served as fact without the
        pending label, and an answer with no sourced rows behind it at all is
        refused outright — which the old gate did not catch.
        """
        if state["grade"] != Grade.SUFFICIENT.value:
            return _FALLBACK_GAP
        if not backing:
            # Nothing sourced to hand over: an "answer" here would be an empty
            # checklist wearing a verified badge.
            return _FALLBACK_GAP
        has_unverified = any(
            source.verification_status != VerificationStatus.VERIFIED for source in backing
        )
        weakest = min(source.confidence for source in backing)
        if has_unverified and weakest < self._confidence_threshold:
            return _FALLBACK_LOW_CONFIDENCE
        return None

    # ── served pack ──────────────────────────────────────────────
    def _build_pack(self, state: GraphState, facts: _Facts) -> ActionPack:
        if facts.service is None:  # defensive: routing should never bring us here
            return self._fallback_pack(state, _FALLBACK_GAP)

        estimated_cost = sum((line.amount_lkr for line in facts.fees), Decimal("0"))
        return ActionPack(
            service_label=self._service_label(facts.service, facts.variant, facts.variants),
            district=state["slots"].get("district"),
            documents=tuple(facts.documents),
            fees=tuple(facts.fees),
            office=facts.office,
            steps=tuple(
                self._steps(facts.service, facts.variant, facts.documents, facts.fees, facts.office)
            ),
            estimated_cost_lkr=estimated_cost,
            # Both label and citations describe the rows above, so both come from
            # the sources backing them — matching the UI's promise that "every
            # requirement above is based on these official sources".
            verification=self._verification(facts.backing_sources),
            citations=tuple(self._source_citations(facts.backing_sources)),
        )

    def _fallback_pack(self, state: GraphState, message: str) -> ActionPack:
        service_id = state["service_id"]
        service = self._store.get_service(service_id) if service_id is not None else None
        office = (
            self._office(service_id, state["slots"].get("district"))
            if service_id is not None
            else None
        )
        # Only cite chunks that are actually about the identified service. When the
        # service is unknown (a true gap, e.g. an unseen tax query), A4's closest
        # chunks belong to *other* services — citing them would mislead the citizen.
        citations: list[Citation] = (
            self._citations(state["retrieved"]) if service_id is not None else []
        )
        contact = _CONTACT_OFFICE if office is not None else _CONTACT_GENERIC
        return ActionPack(
            service_label=service.name_en if service is not None else "Your request",
            district=state["slots"].get("district"),
            documents=(),
            fees=(),
            office=office,
            steps=(_STEP_OFFICE if office is not None else _STEP_GENERIC,),
            estimated_cost_lkr=Decimal("0"),
            # A fallback never claims a verified answer for this request.
            verification=ActionPackVerification.NEWLY_GATHERED_PENDING_VERIFICATION,
            citations=tuple(citations),
            fallback=True,
            fallback_message=message + contact,
        )

    # ── fact assembly (deterministic, grounded) ──────────────────
    def _documents(self, variant: ServiceVariant | None) -> list[DocumentItem]:
        if variant is None or variant.id is None:
            return []
        return [
            DocumentItem(
                name=req.document_name,
                mandatory=req.is_mandatory,
                source_id=req.source_id,
                notes=req.notes,
            )
            for req in self._store.get_requirements(variant.id)
        ]

    def _fees(self, variant: ServiceVariant | None) -> list[FeeLine]:
        if variant is None or variant.id is None:
            return []
        return [
            FeeLine(
                label=fee.label,
                amount_lkr=fee.amount_lkr,
                source_id=fee.source_id,
                notes=fee.notes,
            )
            for fee in self._store.get_fees(variant.id)
        ]

    def _office(self, service_id: int | None, district: str | None) -> ActionPackOffice | None:
        if service_id is None:
            return None
        offices = self._store.get_offices(service_id, district=district)
        if not offices and district is not None:
            offices = self._store.get_offices(service_id)  # relax the district filter
        if not offices:
            return None
        return self._to_action_office(offices[0])

    @staticmethod
    def _to_action_office(office: Office) -> ActionPackOffice:
        return ActionPackOffice(
            name=office.name,
            address=office.address,
            hours=office.hours,
            contact=office.contact,
            district=office.district,
        )

    # ── steps (LLM-sequenced, with a deterministic fallback) ─────
    def _steps(
        self,
        service: Service,
        variant: ServiceVariant | None,
        documents: list[DocumentItem],
        fees: list[FeeLine],
        office: ActionPackOffice | None,
    ) -> list[str]:
        if self._llm is None:
            return self._default_steps(documents, fees, office)
        result = self._llm.complete_structured(
            self._steps_prompt(service, variant, documents, fees, office),
            ActionSteps,
            system=_SYSTEM,
        )
        return result.steps or self._default_steps(documents, fees, office)

    @staticmethod
    def _default_steps(
        documents: list[DocumentItem],
        fees: list[FeeLine],
        office: ActionPackOffice | None,
    ) -> list[str]:
        steps: list[str] = []
        if documents:
            steps.append("Collect all the documents listed above.")
        if office is not None:
            steps.append(f"Visit {office.name} ({office.address}).")
        else:
            steps.append("Visit the relevant office for your district.")
        if fees:
            steps.append("Pay the listed fees and keep the receipts.")
        steps.append("Submit your application and retain the acknowledgement.")
        return steps

    @staticmethod
    def _steps_prompt(
        service: Service,
        variant: ServiceVariant | None,
        documents: list[DocumentItem],
        fees: list[FeeLine],
        office: ActionPackOffice | None,
    ) -> str:
        doc_lines = "\n".join(f"- {item.name}" for item in documents) or "- (none)"
        fee_lines = (
            "\n".join(f"- {fee.label}: LKR {fee.amount_lkr}" for fee in fees) or "- (none)"
        )
        office_line = f"{office.name}, {office.address}" if office is not None else "(unknown)"
        condition = f" ({variant.condition_label})" if variant is not None else ""
        return (
            f"Service: {service.name_en}{condition}\n"
            f"Documents:\n{doc_lines}\n"
            f"Fees:\n{fee_lines}\n"
            f"Office: {office_line}\n\n"
            "Write the ordered steps the citizen should follow."
        )

    # ── provenance & labelling ───────────────────────────────────
    @staticmethod
    def _verification(backing: list[Source]) -> ActionPackVerification:
        """Label the pack by the provenance of the rows it actually renders."""
        all_verified = backing and all(
            source.verification_status == VerificationStatus.VERIFIED for source in backing
        )
        return (
            ActionPackVerification.VERIFIED
            if all_verified
            else ActionPackVerification.NEWLY_GATHERED_PENDING_VERIFICATION
        )

    @staticmethod
    def _source_citations(backing: list[Source]) -> list[Citation]:
        """Cite the sources behind the documents and fees shown, in that order."""
        return [
            Citation(
                title=source.title,
                url=source.url,
                last_verified=source.retrieved_date,
                source_id=source.id,
            )
            for source in backing
        ]

    @staticmethod
    def _citations(retrieved: list[dict[str, Any]]) -> list[Citation]:
        """Citations drawn from retrieved evidence — used only by the fallback pack,
        which has no rendered rows of its own to point at."""
        seen: set[int | None] = set()
        citations: list[Citation] = []
        for chunk in retrieved:
            source_id = chunk["source_id"]
            if source_id in seen:
                continue
            seen.add(source_id)
            citations.append(
                Citation(
                    title=str(chunk["source_title"]),
                    url=chunk["source_url"],
                    last_verified=date.fromisoformat(str(chunk["last_verified"])),
                    source_id=source_id,
                )
            )
        return citations

    # ── misc ─────────────────────────────────────────────────────
    @staticmethod
    def _pick_variant(
        variant_id: int | None, variants: list[ServiceVariant]
    ) -> ServiceVariant | None:
        if variant_id is not None:
            match = next((v for v in variants if v.id == variant_id), None)
            if match is not None:
                return match
        return variants[0] if variants else None

    @staticmethod
    def _service_label(
        service: Service, variant: ServiceVariant | None, variants: list[ServiceVariant]
    ) -> str:
        if variant is not None and len(variants) > 1 and variant.condition_label:
            return f"{service.name_en} ({variant.condition_label})"
        return service.name_en
