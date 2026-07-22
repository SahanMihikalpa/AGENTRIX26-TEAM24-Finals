"""Mappers between domain dataclasses and the JSON-serialisable ``GraphState``.

The blackboard only holds primitives (so it survives checkpointing), so domain
value objects are flattened here at the boundary. Money is serialised as a
**string** to preserve :class:`~decimal.Decimal` precision (the same choice the
data layer makes storing ``amount_lkr`` as TEXT); the API layer renders it to a
JSON number for the wire (docs/11).
"""

from __future__ import annotations

from typing import Any

from app.domain.entities import ActionPack, Citation, RetrievedChunk


def retrieved_to_state(chunk: RetrievedChunk) -> dict[str, Any]:
    """Flatten an A4 :class:`RetrievedChunk` (chunk text + provenance) for state."""
    source = chunk.source
    return {
        "content": chunk.content,
        "score": chunk.score,
        "service_id": chunk.service_id,
        "chunk_index": chunk.chunk_index,
        "source_id": source.id,
        "source_title": source.title,
        "source_url": source.url,
        "verification_status": source.verification_status.value,
        "confidence": source.confidence,
        "last_verified": source.retrieved_date.isoformat(),
    }


def citation_to_state(citation: Citation) -> dict[str, Any]:
    return {
        "source_id": citation.source_id,
        "title": citation.title,
        "url": citation.url,
        "last_verified": citation.last_verified.isoformat(),
    }


def action_pack_to_state(pack: ActionPack) -> dict[str, Any]:
    """Serialise the A6 :class:`ActionPack` artifact into the state ``answer`` dict."""
    return {
        "service_label": pack.service_label,
        "district": pack.district,
        "documents": [
            {
                "name": item.name,
                "mandatory": item.mandatory,
                "source_id": item.source_id,
                "notes": item.notes,
            }
            for item in pack.documents
        ],
        "fees": [
            {
                "label": fee.label,
                "amount_lkr": str(fee.amount_lkr),
                "source_id": fee.source_id,
                "notes": fee.notes,
            }
            for fee in pack.fees
        ],
        "office": (
            {
                "name": pack.office.name,
                "address": pack.office.address,
                "hours": pack.office.hours,
                "contact": pack.office.contact,
                "district": pack.office.district,
            }
            if pack.office is not None
            else None
        ),
        "steps": list(pack.steps),
        "estimated_cost_lkr": str(pack.estimated_cost_lkr),
        "verification": pack.verification.value,
        "citations": [citation_to_state(citation) for citation in pack.citations],
        "fallback": pack.fallback,
        "fallback_message": pack.fallback_message,
    }
