"""
Inventory router — /api/v1/inventory endpoints.

GET  /inventory/summary            — aggregate health numbers
GET  /inventory/                   — paginated list with analysis
GET  /inventory/reorder-suggestions — products needing reorder
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.models.user import User
from app.schemas.inventory import (
    InventoryItem,
    InventoryListResponse,
    InventorySummary,
    ReorderSuggestion,
)
from app.services import inventory_service

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get(
    "/summary",
    response_model=InventorySummary,
    dependencies=[Depends(require_role("viewer"))],
)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventorySummary:
    """Aggregate inventory health: counts and total value."""
    data = await inventory_service.get_inventory_summary(db, org_id=current_user.org_id)
    return InventorySummary(**data)


@router.get(
    "/",
    response_model=InventoryListResponse,
    dependencies=[Depends(require_role("viewer"))],
)
async def list_inventory(
    status: str | None = Query(None, description="Filter by status: ok|low|critical|overstock"),
    category: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventoryListResponse:
    """
    Paginated inventory list with safety stock, EOQ, ABC class, and stock status.
    ⚠️ Data is SYNTHETIC unless stated otherwise.
    """
    data = await inventory_service.get_inventory_list(
        db,
        org_id=current_user.org_id,
        status_filter=status,
        category=category,
        limit=limit,
        offset=offset,
    )
    return InventoryListResponse(
        items=[InventoryItem(**i) for i in data["items"]],
        total=data["total"],
        low_stock_count=data["low_stock_count"],
        critical_count=data["critical_count"],
    )


@router.get(
    "/reorder-suggestions",
    response_model=list[ReorderSuggestion],
    dependencies=[Depends(require_role("viewer"))],
)
async def reorder_suggestions(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReorderSuggestion]:
    """
    Products that should be reordered, ranked by urgency.
    Uses EOQ formula with synthetic cost parameters.
    """
    suggestions = await inventory_service.get_reorder_suggestions(
        db, org_id=current_user.org_id, limit=limit
    )
    return [ReorderSuggestion(**s) for s in suggestions]
