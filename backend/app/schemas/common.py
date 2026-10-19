"""
Common Pydantic schemas shared across the API.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Response from the /health endpoint."""

    status: str
    timestamp: str
    version: str
    services: dict[str, str]


class ErrorResponse(BaseModel):
    """Standard error response body."""

    error: str
    detail: dict = Field(default_factory=dict)


class DateRangeFilter(BaseModel):
    """Reusable date range query parameters."""

    start_date: date | None = None
    end_date: date | None = None


class PaginationParams(BaseModel):
    """Reusable pagination query parameters."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel):
    """Wrapper for paginated list responses."""

    model_config = ConfigDict(from_attributes=True)

    items: list = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int


class OrgRead(BaseModel):
    """Read-only org representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    created_at: datetime


class UserRead(BaseModel):
    """Read-only user representation (no password)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
