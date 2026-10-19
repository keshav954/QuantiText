"""
Analytics models — DailySales (pre-aggregated), Forecast, and Anomaly.
DailySales is populated by the ETL; Forecast and Anomaly by ML pipelines.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class DailySales(UUIDPrimaryKeyMixin, Base):
    """Pre-aggregated daily sales per product per region. Fed by ETL."""

    __tablename__ = "daily_sales"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sale_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    quantity_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<DailySales {self.sale_date} product={self.product_id}>"


class Forecast(UUIDPrimaryKeyMixin, Base):
    """Model forecast output — one row per product per forecast date per model."""

    __tablename__ = "forecasts"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_qty: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    lower_bound: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    upper_bound: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    mape: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Forecast {self.forecast_date} model={self.model_name}>"


class Anomaly(UUIDPrimaryKeyMixin, Base):
    """Detected anomaly — one row per product per detection event."""

    __tablename__ = "anomalies"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    detected_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    anomaly_type: Mapped[str] = mapped_column(String(100), nullable=False)
    detector: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # zscore | iforest | data_quality
    severity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    estimated_impact: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    alert = None  # Set by Alert.anomaly backref

    def __repr__(self) -> str:
        return f"<Anomaly {self.detected_date} type={self.anomaly_type}>"
