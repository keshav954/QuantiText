"""
Anomaly & Alert router — /api/v1/anomaly and /api/v1/alerts endpoints.

POST /anomaly/detect               — trigger detection run (manager+)
GET  /anomaly/                     — list anomalies
POST /anomaly/{id}/dismiss         — dismiss an anomaly (analyst+)

GET  /alerts/                      — list alerts
POST /alerts/mark-read             — mark alerts as read
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.models.user import User
from app.schemas.anomaly import (
    AlertListResponse,
    AlertOut,
    AnomalyListResponse,
    AnomalyOut,
    DetectionRunResult,
    DismissRequest,
    MarkReadRequest,
)
from app.services import anomaly_service

router = APIRouter(tags=["anomaly"])


# ── Detection ──────────────────────────────────────────────────────────────────

@router.post(
    "/anomaly/detect",
    response_model=DetectionRunResult,
    dependencies=[Depends(require_role("manager"))],
)
async def trigger_detection(
    lookback_days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DetectionRunResult:
    """
    Run all anomaly detectors (Z-score, Isolation Forest, data quality)
    over the past `lookback_days` and persist new anomalies and alerts.
    """
    result = await anomaly_service.run_detection(
        db, org_id=current_user.org_id, lookback_days=lookback_days
    )
    return DetectionRunResult(**result)


# ── Anomalies ──────────────────────────────────────────────────────────────────

@router.get(
    "/anomaly/",
    response_model=AnomalyListResponse,
    dependencies=[Depends(require_role("viewer"))],
)
async def list_anomalies(
    only_active: bool = Query(True, description="Exclude dismissed anomalies"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnomalyListResponse:
    data = await anomaly_service.get_anomalies(
        db,
        org_id=current_user.org_id,
        only_active=only_active,
        limit=limit,
        offset=offset,
    )
    return AnomalyListResponse(
        items=[AnomalyOut(**i) for i in data["items"]],
        total=data["total"],
    )


@router.post(
    "/anomaly/{anomaly_id}/dismiss",
    dependencies=[Depends(require_role("analyst"))],
)
async def dismiss_anomaly(
    anomaly_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    found = await anomaly_service.dismiss_anomaly(
        db, org_id=current_user.org_id, anomaly_id=anomaly_id
    )
    if not found:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anomaly not found")
    return {"status": "dismissed"}


# ── Alerts ─────────────────────────────────────────────────────────────────────

@router.get(
    "/alerts/",
    response_model=AlertListResponse,
    dependencies=[Depends(require_role("viewer"))],
)
async def list_alerts(
    only_unread: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertListResponse:
    data = await anomaly_service.get_alerts(
        db,
        org_id=current_user.org_id,
        only_unread=only_unread,
        limit=limit,
        offset=offset,
    )
    return AlertListResponse(
        items=[AlertOut(**i) for i in data["items"]],
        unread_count=data["unread_count"],
    )


@router.post(
    "/alerts/mark-read",
    dependencies=[Depends(require_role("viewer"))],
)
async def mark_alerts_read(
    body: MarkReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    count = await anomaly_service.mark_alerts_read(
        db, org_id=current_user.org_id, alert_ids=body.alert_ids
    )
    return {"marked_read": count}
