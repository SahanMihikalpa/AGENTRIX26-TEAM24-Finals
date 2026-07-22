"""Feedback delivery — ``POST /api/experience-reports`` (doc/11 §2, FR-6).

A citizen files a post-visit report; the backend persists it and best-effort feeds
it through the B2→B3 pipeline (see :class:`ExperienceReportIntake`). When the
request omits ``service_id`` / district, they are resolved from the session's
checkpointed state, so the report is tied to the service the conversation was about.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dto import ExperienceReportRequest, ExperienceReportResponse
from app.api.runtime import AppRuntime, get_runtime
from app.api.session_state import session_values
from app.domain.entities import ExperienceReport, ReportStatus

router = APIRouter(prefix="/api", tags=["feedback"])

RuntimeDep = Annotated[AppRuntime, Depends(get_runtime)]


@router.post(
    "/experience-reports", response_model=ExperienceReportResponse, status_code=201
)
async def submit_experience_report(
    request: ExperienceReportRequest, runtime: RuntimeDep
) -> ExperienceReportResponse:
    """File an experience report; resolve service/district from the session if absent."""
    service_id = request.service_id
    district = ""
    if request.session_id:
        values = session_values(runtime.graph, request.session_id)
        if service_id is None and values.get("service_id") is not None:
            service_id = int(values["service_id"])
        district = str((values.get("slots") or {}).get("district") or "")

    report = ExperienceReport(
        service_id=service_id,
        district=district,
        report_text=request.text,
        reported_outcome=request.outcome,
        status=ReportStatus.PENDING,
        created_at=datetime.now(UTC),
    )
    saved = runtime.experience_intake.submit(report)
    if saved.id is None:  # pragma: no cover — the store always assigns an id
        raise HTTPException(status_code=500, detail="failed to persist experience report")
    return ExperienceReportResponse(id=saved.id, status=saved.status.value)
