"""
Reports & Approvals router — /api/v1/reports.

POST /reports/generate           — generate a new report (on-demand)
GET  /reports                    — list reports
GET  /reports/{id}               — get report detail
GET  /reports/{id}/export        — export report as text
GET  /reports/recommendations    — list recommendations
POST /reports/recommendations/{id}/decide — approve/reject
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.core.audit import log_audit
from app.models.user import User
from app.schemas.report import (
    RecommendationDecision,
    RecommendationListResponse,
    ReportDetail,
    ReportGenerateRequest,
    ReportListResponse,
)
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "/generate",
    response_model=ReportDetail,
    status_code=201,
    dependencies=[Depends(require_role("analyst"))],
)
async def generate_report(
    body: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportDetail:
    """Generate a new business report with aggregated data and LLM narrative."""
    result = await report_service.generate_report(
        db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        title=body.title,
        report_type=body.report_type,
    )

    await log_audit(
        db,
        action="generate",
        resource="report",
        resource_id=str(result["id"]),
        user_id=current_user.id,
        org_id=current_user.org_id,
    )

    return ReportDetail(**result)


@router.get(
    "",
    response_model=ReportListResponse,
    dependencies=[Depends(require_role("viewer"))],
)
async def list_reports(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportListResponse:
    """List all reports for the current org."""
    result = await report_service.list_reports(
        db, org_id=current_user.org_id, limit=limit, offset=offset
    )
    return ReportListResponse(**result)


@router.get(
    "/{report_id}",
    response_model=ReportDetail,
    dependencies=[Depends(require_role("viewer"))],
)
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportDetail:
    """Get full report detail including aggregated data."""
    result = await report_service.get_report(db, org_id=current_user.org_id, report_id=report_id)
    if not result:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportDetail(**result)


@router.get(
    "/{report_id}/export",
    response_class=PlainTextResponse,
    dependencies=[Depends(require_role("viewer"))],
)
async def export_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlainTextResponse:
    """Export a report as formatted plain text."""
    text_content = await report_service.export_report_text(
        db, org_id=current_user.org_id, report_id=report_id
    )
    if not text_content:
        raise HTTPException(status_code=404, detail="Report not found")

    await log_audit(
        db,
        action="export",
        resource="report",
        resource_id=str(report_id),
        user_id=current_user.id,
        org_id=current_user.org_id,
    )

    return PlainTextResponse(
        content=text_content,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=report_{report_id}.txt"},
    )


# ── Recommendations ───────────────────────────────────────────────────────────


@router.get(
    "/recommendations",
    response_model=RecommendationListResponse,
    dependencies=[Depends(require_role("viewer"))],
)
async def list_recommendations(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationListResponse:
    """List recommendations with optional status filter."""
    result = await report_service.list_recommendations(
        db,
        org_id=current_user.org_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return RecommendationListResponse(**result)


@router.post(
    "/recommendations/{recommendation_id}/decide",
    dependencies=[Depends(require_role("manager"))],
)
async def decide_recommendation(
    recommendation_id: uuid.UUID,
    body: RecommendationDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Approve or reject a recommendation (manager+ only)."""
    updated = await report_service.decide_recommendation(
        db,
        org_id=current_user.org_id,
        recommendation_id=recommendation_id,
        action=body.action,
        user_id=current_user.id,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found or already decided",
        )

    await log_audit(
        db,
        action=body.action,
        resource="recommendation",
        resource_id=str(recommendation_id),
        user_id=current_user.id,
        org_id=current_user.org_id,
    )

    return {"status": "ok", "action": body.action, "recommendation_id": recommendation_id}
