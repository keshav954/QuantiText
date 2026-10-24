"""
KPI router — dashboard data endpoints with date/category/region filters.
All endpoints require at least viewer role.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_redis, require_role
from app.core.audit import get_client_ip, log_audit
from app.models.user import User
from app.schemas.kpi import KPISummary, RevenueTrendResponse, TopProductsResponse
from app.services import kpi_service

router = APIRouter(prefix="/kpi", tags=["kpi"])


@router.get(
    "/summary",
    response_model=KPISummary,
    dependencies=[Depends(require_role("viewer"))],
)
async def kpi_summary(
    request: Request,
    start_date: date | None = Query(None, description="Filter start date"),
    end_date: date | None = Query(None, description="Filter end date"),
    category: str | None = Query(None, description="Filter by category name"),
    region: str | None = Query(None, description="Filter by region"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
) -> KPISummary:
    """
    Top-level KPI cards: total revenue, orders, AOV, unique customers.
    Includes trend percentage vs previous period when date range is provided.
    Cached in Redis for 5 minutes.
    """
    data = await kpi_service.get_kpi_summary(
        db,
        redis,
        org_id=current_user.org_id,
        start_date=start_date,
        end_date=end_date,
        category=category,
        region=region,
    )
    await log_audit(
        db,
        action="view_kpi_summary",
        resource="kpi",
        user_id=current_user.id,
        org_id=current_user.org_id,
        ip_address=get_client_ip(request),
        details={"category": category, "region": region},
    )
    return KPISummary(**data)


@router.get(
    "/revenue-trend",
    response_model=RevenueTrendResponse,
    dependencies=[Depends(require_role("viewer"))],
)
async def revenue_trend(
    request: Request,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
) -> RevenueTrendResponse:
    """
    Daily revenue and order count time series for charting.
    """
    data = await kpi_service.get_revenue_trend(
        db,
        redis,
        org_id=current_user.org_id,
        start_date=start_date,
        end_date=end_date,
    )
    await log_audit(
        db,
        action="view_revenue_trend",
        resource="kpi",
        user_id=current_user.id,
        org_id=current_user.org_id,
        ip_address=get_client_ip(request),
    )
    return RevenueTrendResponse(**data)


@router.get(
    "/top-products",
    response_model=TopProductsResponse,
    dependencies=[Depends(require_role("viewer"))],
)
async def top_products(
    request: Request,
    limit: int = Query(10, ge=1, le=50, description="Number of products to return"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
) -> TopProductsResponse:
    """
    Top N products ranked by total revenue.
    """
    data = await kpi_service.get_top_products(
        db,
        redis,
        org_id=current_user.org_id,
        limit=limit,
    )
    await log_audit(
        db,
        action="view_top_products",
        resource="kpi",
        user_id=current_user.id,
        org_id=current_user.org_id,
        ip_address=get_client_ip(request),
        details={"limit": limit},
    )
    return TopProductsResponse(**data)
