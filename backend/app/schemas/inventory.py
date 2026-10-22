"""
Inventory schemas — response models for inventory analysis endpoints.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class InventoryItem(BaseModel):
    """Single product's inventory record with computed analysis fields."""

    product_id: UUID
    sku: str
    product_name: str
    category: str | None = None

    # Raw stock fields
    stock_on_hand: int
    reorder_point: int
    lead_time_days: int
    min_order_qty: int
    unit_cost: float
    holding_cost_pct: float

    # Computed fields (filled by service)
    avg_daily_demand: float | None = None
    safety_stock: int | None = None
    eoq: int | None = None  # Economic Order Quantity
    days_of_stock: float | None = None
    abc_class: str | None = None  # A / B / C
    status: str | None = None  # ok | low | critical | overstock
    last_updated: datetime | None = None


class InventoryListResponse(BaseModel):
    """Paginated inventory list with summary counts."""

    items: list[InventoryItem]
    total: int
    low_stock_count: int
    critical_count: int


class InventorySummary(BaseModel):
    """Aggregate inventory health numbers for the dashboard strip."""

    total_products: int
    low_stock_count: int
    critical_count: int
    overstock_count: int
    total_inventory_value: float


class ReorderSuggestion(BaseModel):
    """Suggested reorder quantity for a product."""

    product_id: UUID
    sku: str
    product_name: str
    current_stock: int
    reorder_point: int
    eoq: int
    suggested_qty: int
    estimated_cost: float
    urgency: str  # immediate | soon | watch


class WhatIfRequest(BaseModel):
    """Parameters for inventory what-if scenario simulation."""

    demand_change_pct: float = 0.0  # e.g. +20.0 for 20% surge, -10.0 for drop
    lead_time_delay_days: int = 0  # e.g. +7 days supplier delay
    product_id: UUID | None = None  # None = simulate all products


class WhatIfItemResult(BaseModel):
    """Simulated inventory metrics for a product under what-if conditions."""

    product_id: UUID
    sku: str
    product_name: str
    baseline_stock_on_hand: int
    baseline_safety_stock: int
    baseline_reorder_point: int
    baseline_days_of_stock: float
    simulated_safety_stock: int
    simulated_reorder_point: int
    simulated_days_of_stock: float
    stockout_risk: str  # high | medium | low | none
    stockout_in_days: float | None = None
    projected_reorder_qty: int
    projected_additional_cost: float


class WhatIfResponse(BaseModel):
    """Summary and details of simulated inventory scenario."""

    scenario_name: str
    demand_change_pct: float
    lead_time_delay_days: int
    items: list[WhatIfItemResult]
    total_stockout_risks: int
    estimated_capital_impact: float
    synthetic_notice: str = "⚠️ SYNTHETIC SIMULATION — All parameters and projections are simulated."
