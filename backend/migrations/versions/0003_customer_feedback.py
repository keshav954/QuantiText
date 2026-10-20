"""Add customer_feedback table for hybrid RAG

Revision ID: 0003_customer_feedback
Revises: 0002_chat_tables
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_customer_feedback"
down_revision: str | None = "0002_chat_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customer_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("rating", sa.Integer, nullable=True),
        sa.Column("text_content", sa.Text, nullable=False),
        sa.Column("sentiment", sa.String(20), nullable=True),
        sa.Column("sentiment_score", sa.Float, nullable=True),
        sa.Column("themes", postgresql.JSONB, nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("feedback_date", sa.Date, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_customer_feedback_org_id", "customer_feedback", ["org_id"])
    op.create_index("ix_customer_feedback_product_id", "customer_feedback", ["product_id"])
    op.create_index("ix_customer_feedback_date", "customer_feedback", ["feedback_date"])

    # Grant read access to the BI readonly role
    op.execute("GRANT SELECT ON customer_feedback TO bi_readonly;")


def downgrade() -> None:
    op.execute("REVOKE SELECT ON customer_feedback FROM bi_readonly;")
    op.drop_table("customer_feedback")
