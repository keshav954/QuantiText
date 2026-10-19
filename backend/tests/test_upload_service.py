"""
Tests for the upload/admin endpoints and upload service helpers.
"""

import pytest
import uuid


@pytest.mark.asyncio
async def test_upload_requires_auth(async_client):
    """POST /api/v1/admin/upload should require authentication."""
    response = await async_client.post("/api/v1/admin/upload")
    assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_upload_preview_requires_auth(async_client):
    """POST /api/v1/admin/upload/preview should require authentication."""
    response = await async_client.post(
        "/api/v1/admin/upload/preview",
        json={"filename": "test.csv"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_upload_validate_requires_auth(async_client):
    """POST /api/v1/admin/upload/validate should require authentication."""
    response = await async_client.post(
        "/api/v1/admin/upload/validate",
        json={
            "filename": "test.csv",
            "mappings": [{"source_column": "a", "target_column": "invoice_no", "transform": None}],
        },
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_upload_confirm_requires_auth(async_client):
    """POST /api/v1/admin/upload/confirm should require authentication."""
    response = await async_client.post(
        "/api/v1/admin/upload/confirm",
        json={
            "filename": "test.csv",
            "mappings": [{"source_column": "a", "target_column": "invoice_no", "transform": None}],
            "replace_existing": False,
        },
    )
    assert response.status_code in (401, 403)


def test_auto_map_columns():
    """Column auto-detection should map known synonyms correctly."""
    from app.services.upload_service import _auto_map_columns

    source_cols = ["InvoiceNo", "InvoiceDate", "StockCode", "Description", "Quantity", "UnitPrice", "CustomerID", "Country"]
    mappings = _auto_map_columns(source_cols)

    target_cols = {m["target_column"] for m in mappings}
    assert "invoice_no" in target_cols
    assert "quantity" in target_cols
    assert "unit_price" in target_cols


def test_auto_map_empty():
    """Auto-map should return empty list for unrecognized columns."""
    from app.services.upload_service import _auto_map_columns

    mappings = _auto_map_columns(["foo", "bar", "baz"])
    assert len(mappings) == 0
