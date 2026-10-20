"""
Customer feedback model — stores reviews, survey responses, and support tickets
with sentiment analysis and vector embeddings for hybrid RAG.

⚠️  Feedback data is SYNTHETIC unless stated otherwise.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class CustomerFeedback(UUIDPrimaryKeyMixin, Base):
    """
    Unstructured customer feedback with embeddings for vector search.

    The embedding column stores all-MiniLM-L6-v2 output (384 dimensions)
    in pgvector format for similarity queries.
    """

    __tablename__ = "customer_feedback"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="review | survey | support_ticket",
    )
    rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="1-5 star rating, if applicable",
    )
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="positive | negative | neutral | mixed",
    )
    sentiment_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Continuous sentiment score: -1.0 (negative) to 1.0 (positive)",
    )
    themes: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment='Extracted themes, e.g. ["delivery_delay", "quality_issue"]',
    )
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    feedback_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # Note: The embedding column is created via Alembic migration using pgvector.
    # It's defined as: embedding vector(384)
    # We don't use a mapped_column here because SQLAlchemy needs the pgvector
    # extension registered. The migration handles the column creation.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<CustomerFeedback {self.source} sentiment={self.sentiment}>"
