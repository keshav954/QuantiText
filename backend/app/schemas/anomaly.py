"""
Anomaly and Alert schemas — response models for detection and alert endpoints.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class AnomalyOut(BaseModel):
    """Single anomaly detection result."""

    id: UUID
    product_id: UUID | None = None
    sku: str | None = None
    product_name: str | None = None
    detected_date: date
    anomaly_type: str  # revenue_spike | revenue_drop | zero_sales | inventory_critical
    detector: str  # zscore | iforest | data_quality
    severity_score: float  # 0–1
    estimated_impact: float | None = None
    details: dict | None = None
    is_dismissed: bool
    created_at: datetime


class AnomalyListResponse(BaseModel):
    items: list[AnomalyOut]
    total: int


class AlertOut(BaseModel):
    """User-facing alert record."""

    id: UUID
    anomaly_id: UUID | None = None
    title: str
    description: str | None = None
    severity: str  # critical | warning | info
    is_read: bool
    created_at: datetime


class AlertListResponse(BaseModel):
    items: list[AlertOut]
    unread_count: int


class DismissRequest(BaseModel):
    anomaly_id: UUID


class MarkReadRequest(BaseModel):
    alert_ids: list[UUID]


class DetectionRunResult(BaseModel):
    """Result of a manual detection run."""

    new_anomalies: int
    new_alerts: int
    recommendations_created: int = 0
    period_checked: str
