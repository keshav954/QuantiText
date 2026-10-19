"""
Organization model — top-level tenant entity.
All tenant-scoped data links back here via org_id.
"""

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Org(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orgs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    users = relationship("User", back_populates="org", lazy="selectin")
    products = relationship("Product", back_populates="org", lazy="selectin")
    categories = relationship("Category", back_populates="org", lazy="selectin")
    customers = relationship("Customer", back_populates="org", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Org {self.slug}>"
