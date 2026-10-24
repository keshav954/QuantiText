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

from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.core.audit import get_client_ip, log_audit
from app.models.user import User
from app.schemas.anomaly import (
    AlertListResponse,
    AlertOut,
    AnomalyListResponse,
    AnomalyOut,
    DetectionRunResult,
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
    request: Request,
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
    await log_audit(
        db,
        action="anomaly_detection_run",
        resource="anomaly",
        user_id=current_user.id,
        org_id=current_user.org_id,
        details={
            "lookback_days": lookback_days,
            "anomalies_detected": result.get("anomalies_detected", 0),
            "alerts_created": result.get("alerts_created", 0),
        },
        ip_address=get_client_ip(request),
    )
    return DetectionRunResult(**result)


@router.post(
    "/anomaly/closed-loop",
    dependencies=[Depends(require_role("manager"))],
)
async def trigger_closed_loop(
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Execute closed-loop pipeline for unresolved anomalies:
    anomaly -> root cause -> forecast impact -> recommendation.
    """
    from app.services import closed_loop_service

    result = await closed_loop_service.process_closed_loop_for_org(
        db, org_id=current_user.org_id, limit=limit
    )
    await log_audit(
        db,
        action="trigger_closed_loop",
        resource="anomaly",
        user_id=current_user.id,
        org_id=current_user.org_id,
        details={
            "anomalies_evaluated": result["anomalies_evaluated"],
            "recommendations_created": result["recommendations_created"],
        },
        ip_address=get_client_ip(request),
    )
    return result


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
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    found = await anomaly_service.dismiss_anomaly(
        db, org_id=current_user.org_id, anomaly_id=anomaly_id
    )
    if not found:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anomaly not found")

    await log_audit(
        db,
        action="dismiss_anomaly",
        resource="anomaly",
        resource_id=str(anomaly_id),
        user_id=current_user.id,
        org_id=current_user.org_id,
        ip_address=get_client_ip(request),
    )
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
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    count = await anomaly_service.mark_alerts_read(
        db, org_id=current_user.org_id, alert_ids=body.alert_ids
    )
    await log_audit(
        db,
        action="mark_alerts_read",
        resource="alert",
        user_id=current_user.id,
        org_id=current_user.org_id,
        details={"marked_read": count, "alert_count": len(body.alert_ids)},
        ip_address=get_client_ip(request),
    )
    return {"marked_read": count}


class AlertConnectionManager:
    """Manages active WebSocket connections subscribed to real-time alerts per org."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, org_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if org_id not in self._connections:
            self._connections[org_id] = set()
        self._connections[org_id].add(websocket)

    def disconnect(self, org_id: str, websocket: WebSocket) -> None:
        if org_id in self._connections:
            self._connections[org_id].discard(websocket)
            if not self._connections[org_id]:
                del self._connections[org_id]

    async def broadcast_to_org(self, org_id: str, message: dict) -> int:
        conns = self._connections.get(str(org_id), set())
        sent = 0
        dead = set()
        for ws in list(conns):
            try:
                await ws.send_json(message)
                sent += 1
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(str(org_id), ws)
        return sent


ws_manager = AlertConnectionManager()


@router.websocket("/alerts/ws")
async def alerts_websocket(websocket: WebSocket, token: str | None = Query(None)) -> None:
    """Real-time alerts WebSocket connection with token authentication and org scoping."""
    if not token:
        await websocket.close(code=1008)
        return

    from app.core.security import decode_access_token

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        await websocket.close(code=1008)
        return

    org_id = str(payload.get("org") or payload.get("org_id") or "")
    if not org_id:
        await websocket.close(code=1008)
        return

    await ws_manager.connect(org_id, websocket)
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "org_id": org_id,
                "message": "QuantiText real-time alerts stream connected",
            }
        )
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(org_id, websocket)
