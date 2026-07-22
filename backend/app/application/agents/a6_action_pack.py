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
)
from app.domain.ports.knowledge import KnowledgeStore
from app.domain.ports.llm import LLMProvider

_SYSTEM = (
    "You write the step-by-step instructions for a citizen completing a Sri "
    "Lankan government process. Use ONLY the documents, fees, and office given. "
    "Produce a short, ordered list of clear, practical steps. Do not invent "
    "documents, fees, amounts, or offices."
)

_FALLBACK_GAP = (
    "We couldn't find verified information for this exact request yet. "
    "Please contact the office below to confirm the requirements directly."
)
_FALLBACK_LOW_CONFIDENCE = (
    "We found a related source but couldn't verify it with enough confidence to "
    "give you a checklist. Please confirm with the office below before relying on it."
)


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
        gate_message = self._gate(state)
        if gate_message is not None:
            pack = self._fallback_pack(state, gate_message)
        else:
            pack = self._build_pack(state)

        answer = action_pack_to_state(pack)
        return {"answer": answer, "citations": answer["citations"]}

    # ── confidence gate (AD-8) ───────────────────────────────────
    def _gate(self, state: GraphState) -> str | None:
        """Return a fallback message if the pack must NOT be rendered, else ``None``."""
        if state["grade"] != Grade.SUFFICIENT.value:
            return _FALLBACK_GAP
        retrieved = state["retrieved"]
        has_unverified = any(
            chunk["verification_status"] != "verified" for chunk in retrieved
        )
        if has_unverified and state["answer_confidence"] < self._confidence_threshold:
            return _FALLBACK_LOW_CONFIDENCE
        return None

    # ── served pack ──────────────────────────────────────────────
    def _build_pack(self, state: GraphState) -> ActionPack:
        service_id = state["service_id"]
        service = self._store.get_service(service_id) if service_id is not None else None
        if service is None:  # defensive: lost the service somehow → fall back
            return self._fallback_pack(state, _FALLBACK_GAP)

        variants = self._store.list_variants(service_id)  # type: ignore[arg-type]
        variant = self._pick_variant(state["variant_id"], variants)

        documents = self._documents(variant)
        fees = self._fees(variant)
        office = self._office(service_id, state["slots"].get("district"))
        estimated_cost = sum((line.amount_lkr for line in fees), Decimal("0"))

        return ActionPack(
            service_label=self._service_label(service, variant, variants),
            district=state["slots"].get("district"),
            documents=tuple(documents),
            fees=tuple(fees),
            office=office,
            steps=tuple(self._steps(service, variant, documents, fees, office)),
            estimated_cost_lkr=estimated_cost,
            verification=self._verification(state["retrieved"]),
            citations=tuple(self._citations(state["retrieved"])),
        )

    def _fallback_pack(self, state: GraphState, message: str) -> ActionPack:
        service_id = state["service_id"]
        service = self._store.get_service(service_id) if service_id is not None else None
        office = (
            self._office(service_id, state["slots"].get("district"))
            if service_id is not None
            else None
        )
        return ActionPack(
            service_label=service.name_en if service is not None else "Your request",
            district=state["slots"].get("district"),
            documents=(),
            fees=(),
            office=office,
            steps=("Contact the office below to confirm the exact requirements.",),
            estimated_cost_lkr=Decimal("0"),
            verification=self._verification(state["retrieved"]),
            citations=tuple(self._citations(state["retrieved"])),
            fallback=True,
            fallback_message=message,
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
    def _verification(retrieved: list[dict[str, Any]]) -> ActionPackVerification:
        all_verified = retrieved and all(
            chunk["verification_status"] == "verified" for chunk in retrieved
        )
        return (
            ActionPackVerification.VERIFIED
            if all_verified
            else ActionPackVerification.NEWLY_GATHERED_PENDING_VERIFICATION
        )

    @staticmethod
    def _citations(retrieved: list[dict[str, Any]]) -> list[Citation]:
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
