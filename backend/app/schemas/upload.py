"""
Upload schemas — request/response models for CSV/Excel data onboarding.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ColumnMapping(BaseModel):
    """Maps a source CSV column to a target schema column."""

    source_column: str
    target_column: str
    transform: str | None = None  # e.g. "to_date", "to_float", "strip"


class UploadPreviewRequest(BaseModel):
    """Request to preview column mappings for an uploaded file."""

    filename: str


class UploadPreviewResponse(BaseModel):
    """Auto-detected columns and suggested mappings."""

    filename: str
    row_count: int
    detected_columns: list[str]
    suggested_mappings: list[ColumnMapping]
    sample_rows: list[dict]  # first 5 rows


class UploadValidationResult(BaseModel):
    """Validation summary for an uploaded file."""

    is_valid: bool
    total_rows: int
    valid_rows: int
    error_count: int
    errors: list[str] = Field(default_factory=list)  # first 20 errors
    warnings: list[str] = Field(default_factory=list)


class UploadConfirmRequest(BaseModel):
    """Confirm and load a validated upload."""

    filename: str
    mappings: list[ColumnMapping]
    replace_existing: bool = False


class UploadResult(BaseModel):
    """Result of loading data into the schema."""

    success: bool
    rows_loaded: int
    products_created: int
    orders_created: int
    message: str


class UploadHistoryItem(BaseModel):
    """Record of a past upload."""

    id: UUID
    filename: str
    status: str  # pending | validated | loaded | failed
    rows: int
    created_at: datetime
