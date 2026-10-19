"""
Inventory model — per-product stock and reorder parameters.
Data is SYNTHETIC unless stated otherwise.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class Inventory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "inventory"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    stock_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_point: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    min_order_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    holding_cost_pct: Mapped[float] = mapped_column(
        Numeric(5, 4), nullable=False, default=0.20
    )  # 20% annual holding cost
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    product = relationship("Product", back_populates="inventory")

    def __repr__(self) -> str:
        return f"<Inventory product={self.product_id} stock={self.stock_on_hand}>"
