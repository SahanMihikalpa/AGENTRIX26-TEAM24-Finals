"""Moderation delivery — the admin queue + promote/reject (doc/11 §2, FR-7).

A thin translator over :class:`ModerationService`: list the sources awaiting review,
and apply a moderator's promote (→ ``verified``) or reject (→ quarantine) decision.
An unknown ``source_id`` yields 404.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dto import ModerationActionResponse, ModerationItemDTO
from app.api.runtime import AppRuntime, get_runtime
from app.domain.entities import Source

router = APIRouter(prefix="/api/moderation", tags=["moderation"])

RuntimeDep = Annotated[AppRuntime, Depends(get_runtime)]


@router.get("/queue", response_model=list[ModerationItemDTO])
async def moderation_queue(runtime: RuntimeDep) -> list[ModerationItemDTO]:
    """List sources still awaiting review (``auto_gathered`` / ``pending``)."""
    return [_to_item(source) for source in runtime.moderation.queue()]


@router.post("/{source_id}/promote", response_model=ModerationActionResponse)
async def promote_source(source_id: int, runtime: RuntimeDep) -> ModerationActionResponse:
    """Promote a source to ``verified``."""
    if not runtime.moderation.promote(source_id):
        raise HTTPException(status_code=404, detail="source not found")
    return ModerationActionResponse(ok=True)


@router.post("/{source_id}/reject", response_model=ModerationActionResponse)
async def reject_source(source_id: int, runtime: RuntimeDep) -> ModerationActionResponse:
    """Reject a source: mark ``rejected`` and de-index it (quarantine)."""
    if not runtime.moderation.reject(source_id):
        raise HTTPException(status_code=404, detail="source not found")
    return ModerationActionResponse(ok=True)


def _to_item(source: Source) -> ModerationItemDTO:
    return ModerationItemDTO(
        source_id=source.id if source.id is not None else 0,
        title=source.title,
        url=source.url,
        source_type=source.source_type.value,
        confidence=source.confidence,
        verification_status=source.verification_status.value,
        retrieved_date=source.retrieved_date.isoformat(),
        published_date=(
            source.published_date.isoformat() if source.published_date else None
        ),
        is_official=source.is_official,
    )
