"""
Report schemas — request/response models for report generation and listing.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    """Request to generate a new report."""

    title: str = Field(max_length=500, default="Weekly Business Report")
    report_type: str = Field(default="on_demand", pattern=r"^(weekly|on_demand)$")


class ReportOut(BaseModel):
    """Read-only representation of a report."""

    id: UUID
    org_id: UUID
    generated_by: UUID | None = None
    title: str
    report_type: str
    narrative: str | None = None
    file_path: str | None = None
    created_at: datetime
    has_data: bool = False  # True if aggregated_data is present


class ReportDetail(ReportOut):
    """Full report detail including aggregated data."""

    aggregated_data: dict | None = None


class ReportListResponse(BaseModel):
    """Paginated report list."""

    items: list[ReportOut]
    total: int


# ── Recommendation / Approval schemas ─────────────────────────────────


class RecommendationOut(BaseModel):
    """Read-only representation of a recommendation."""

    id: UUID
    org_id: UUID
    product_id: UUID | None = None
    product_name: str | None = None
    sku: str | None = None
    action_type: str
    reason: str
    parameters: dict | None = None
    status: str
    approved_by: UUID | None = None
    decided_at: datetime | None = None
    created_at: datetime


class RecommendationDecision(BaseModel):
    """Approve or reject a recommendation."""

    action: str = Field(pattern=r"^(approve|reject)$")


class RecommendationListResponse(BaseModel):
    """Paginated recommendation list."""

    items: list[RecommendationOut]
    total: int
    pending_count: int
