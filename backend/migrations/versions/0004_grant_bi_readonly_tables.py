"""Grant bi_readonly SELECT permissions on supporting tables

Revision ID: 0004_grant_bi_readonly_tables
Revises: 0003_customer_feedback
Create Date: 2026-10-25
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_grant_bi_readonly_tables"
down_revision: str | None = "0003_customer_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Grant read access to tables permitted in Copilot NL2SQL allowlist
    op.execute(
        "GRANT SELECT ON daily_sales, products, categories, forecasts, anomalies TO bi_readonly;"
    )


def downgrade() -> None:
    op.execute(
        "REVOKE SELECT ON daily_sales, products, categories, forecasts, anomalies FROM bi_readonly;"
    )
