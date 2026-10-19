"""
Customer model — anonymised/aggregated customer entity.
No PII stored; only country/region for analytics.
"""

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customers"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    org = relationship("Org", back_populates="customers")
    orders = relationship("Order", back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer {self.customer_code}>"
