"""
Admin/Upload router — /api/v1/admin.

POST /admin/upload                — upload CSV/Excel file
POST /admin/upload/preview        — preview auto-detected columns
POST /admin/upload/validate       — validate data before loading
POST /admin/upload/confirm        — load validated data into schema
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.core.audit import log_audit
from app.models.user import User
from app.schemas.upload import (
    UploadConfirmRequest,
    UploadPreviewRequest,
    UploadPreviewResponse,
    UploadResult,
    UploadValidationResult,
)
from app.services import upload_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/upload",
    dependencies=[Depends(require_role("manager"))],
)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Upload a CSV or Excel file for data onboarding.
    Returns the stored filename for subsequent preview/validate/confirm steps.
    """
    content = await file.read()
    stored_name = await upload_service.save_upload(file.filename or "upload.csv", content)

    await log_audit(
        db,
        action="upload",
        resource="data_file",
        resource_id=stored_name,
        user_id=current_user.id,
        org_id=current_user.org_id,
        details={"original_filename": file.filename, "size_bytes": len(content)},
    )

    return {"filename": stored_name, "size_bytes": len(content)}


@router.post(
    "/upload/preview",
    response_model=UploadPreviewResponse,
    dependencies=[Depends(require_role("manager"))],
)
async def preview_upload(
    body: UploadPreviewRequest,
) -> UploadPreviewResponse:
    """Preview auto-detected column mappings and sample data."""
    result = await upload_service.preview_upload(body.filename)
    return UploadPreviewResponse(**result)


@router.post(
    "/upload/validate",
    response_model=UploadValidationResult,
    dependencies=[Depends(require_role("manager"))],
)
async def validate_upload(
    body: UploadConfirmRequest,
) -> UploadValidationResult:
    """Validate uploaded data against the target schema."""
    result = await upload_service.validate_upload(
        body.filename,
        [m.model_dump() for m in body.mappings],
    )
    return UploadValidationResult(**result)


@router.post(
    "/upload/confirm",
    response_model=UploadResult,
    dependencies=[Depends(require_role("manager"))],
)
async def confirm_upload(
    body: UploadConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadResult:
    """Load validated data into the standard schema."""
    result = await upload_service.load_upload(
        db,
        org_id=current_user.org_id,
        filename=body.filename,
        mappings=[m.model_dump() for m in body.mappings],
        replace_existing=body.replace_existing,
    )

    await log_audit(
        db,
        action="data_load",
        resource="data_file",
        resource_id=body.filename,
        user_id=current_user.id,
        org_id=current_user.org_id,
        details={
            "rows_loaded": result["rows_loaded"],
            "products_created": result["products_created"],
            "replace_existing": body.replace_existing,
        },
    )

    return UploadResult(**result)
