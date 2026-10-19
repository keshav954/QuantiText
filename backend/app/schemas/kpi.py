"""
KPI schemas — request filters and response models.
"""

from datetime import date

from pydantic import BaseModel, Field


class KPIFilter(BaseModel):
    """Query parameters for KPI endpoints."""

    start_date: date | None = None
    end_date: date | None = None
    category: str | None = None
    region: str | None = None


class KPISummary(BaseModel):
    """Top-level KPI card data."""

    total_revenue: float
    total_orders: int
    avg_order_value: float
    unique_customers: int
    # Trend compared to previous period (percentage change)
    revenue_trend: float | None = None
    orders_trend: float | None = None


class RevenueTrendPoint(BaseModel):
    """Single data point for revenue trend chart."""

    date: str  # ISO date string
    revenue: float
    order_count: int


class RevenueTrendResponse(BaseModel):
    """Revenue trend over time."""

    data: list[RevenueTrendPoint]
    period: str  # e.g. "2023-01-01 to 2023-12-31"


class TopProduct(BaseModel):
    """Product ranking entry."""

    product_id: str
    sku: str
    product_name: str
    category: str | None = None
    total_revenue: float
    total_qty: int


class TopProductsResponse(BaseModel):
    """Top N products by revenue."""

    products: list[TopProduct]
    limit: int
