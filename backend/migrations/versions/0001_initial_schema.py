"""Initial schema — all tables, views, and read-only role

Revision ID: 0001
Revises: None
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Orgs ─────────────────────────────────────────────
    op.create_table(
        "orgs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("settings", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_orgs_slug", "orgs", ["slug"])

    # ── Users ────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_users_email", "users", ["email"])

    # ── Categories ───────────────────────────────────────
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_categories_org_id", "categories", ["org_id"])
    op.create_index("ix_categories_slug", "categories", ["slug"])

    # ── Products ─────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_products_org_id", "products", ["org_id"])
    op.create_index("ix_products_sku", "products", ["sku"])

    # ── Customers ────────────────────────────────────────
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("customer_code", sa.String(100), nullable=False),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_customers_org_id", "customers", ["org_id"])
    op.create_index("ix_customers_customer_code", "customers", ["customer_code"])

    # ── Orders ───────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("invoice_no", sa.String(50), nullable=False),
        sa.Column("invoice_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_orders_org_id", "orders", ["org_id"])
    op.create_index("ix_orders_invoice_no", "orders", ["invoice_no"])

    # ── Order Items ──────────────────────────────────────
    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    # ── Inventory ────────────────────────────────────────
    op.create_table(
        "inventory",
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
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("stock_on_hand", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reorder_point", sa.Integer, nullable=False, server_default="0"),
        sa.Column("lead_time_days", sa.Integer, nullable=False, server_default="7"),
        sa.Column("min_order_qty", sa.Integer, nullable=False, server_default="1"),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("holding_cost_pct", sa.Numeric(5, 4), nullable=False, server_default="0.20"),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_inventory_org_id", "inventory", ["org_id"])

    # ── Daily Sales ──────────────────────────────────────
    op.create_table(
        "daily_sales",
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
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sale_date", sa.Date, nullable=False),
        sa.Column("quantity_sold", sa.Integer, nullable=False, server_default="0"),
        sa.Column("revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("region", sa.String(100), nullable=True),
    )
    op.create_index("ix_daily_sales_org_id", "daily_sales", ["org_id"])
    op.create_index("ix_daily_sales_product_id", "daily_sales", ["product_id"])
    op.create_index("ix_daily_sales_sale_date", "daily_sales", ["sale_date"])

    # ── Forecasts ────────────────────────────────────────
    op.create_table(
        "forecasts",
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
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("forecast_date", sa.Date, nullable=False),
        sa.Column("horizon_days", sa.Integer, nullable=False),
        sa.Column("predicted_qty", sa.Numeric(12, 2), nullable=False),
        sa.Column("lower_bound", sa.Numeric(12, 2), nullable=False),
        sa.Column("upper_bound", sa.Numeric(12, 2), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("mape", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_forecasts_org_id", "forecasts", ["org_id"])
    op.create_index("ix_forecasts_product_id", "forecasts", ["product_id"])
    op.create_index("ix_forecasts_forecast_date", "forecasts", ["forecast_date"])

    # ── Anomalies ────────────────────────────────────────
    op.create_table(
        "anomalies",
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
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("detected_date", sa.Date, nullable=False),
        sa.Column("anomaly_type", sa.String(100), nullable=False),
        sa.Column("detector", sa.String(50), nullable=False),
        sa.Column("severity_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("estimated_impact", sa.Numeric(14, 2), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("is_dismissed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_anomalies_org_id", "anomalies", ["org_id"])
    op.create_index("ix_anomalies_detected_date", "anomalies", ["detected_date"])

    # ── Alerts ───────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "anomaly_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("anomalies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_alerts_org_id", "alerts", ["org_id"])

    # ── Recommendations ──────────────────────────────────
    op.create_table(
        "recommendations",
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
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("parameters", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "approved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_recommendations_org_id", "recommendations", ["org_id"])

    # ── Reports ──────────────────────────────────────────
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "generated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False, server_default="on_demand"),
        sa.Column("aggregated_data", postgresql.JSONB, nullable=True),
        sa.Column("narrative", sa.Text, nullable=True),
        sa.Column("file_path", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_reports_org_id", "reports", ["org_id"])

    # ── Audit Log ────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_log_org_id", "audit_log", ["org_id"])
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])

    # ── SQL Views for analytics (read-only, used by NL2SQL) ──

    # v_kpi_daily: daily revenue, order count, AOV, unique customers
    op.execute("""
        CREATE OR REPLACE VIEW v_kpi_daily AS
        SELECT
            o.org_id,
            DATE(o.invoice_date) AS sale_date,
            COUNT(DISTINCT o.id) AS order_count,
            COUNT(DISTINCT o.customer_id) AS unique_customers,
            COALESCE(SUM(o.total_amount), 0) AS total_revenue,
            CASE
                WHEN COUNT(DISTINCT o.id) > 0
                THEN COALESCE(SUM(o.total_amount), 0) / COUNT(DISTINCT o.id)
                ELSE 0
            END AS avg_order_value
        FROM orders o
        GROUP BY o.org_id, DATE(o.invoice_date);
    """)

    # v_sales_by_product: product-level aggregates with category
    op.execute("""
        CREATE OR REPLACE VIEW v_sales_by_product AS
        SELECT
            ds.org_id,
            ds.product_id,
            p.sku,
            p.name AS product_name,
            c.name AS category_name,
            SUM(ds.quantity_sold) AS total_qty,
            SUM(ds.revenue) AS total_revenue,
            MIN(ds.sale_date) AS first_sale,
            MAX(ds.sale_date) AS last_sale
        FROM daily_sales ds
        JOIN products p ON p.id = ds.product_id
        LEFT JOIN categories c ON c.id = p.category_id
        GROUP BY ds.org_id, ds.product_id, p.sku, p.name, c.name;
    """)

    # v_sales_by_region: regional breakdown
    op.execute("""
        CREATE OR REPLACE VIEW v_sales_by_region AS
        SELECT
            ds.org_id,
            COALESCE(ds.region, 'Unknown') AS region,
            ds.sale_date,
            SUM(ds.quantity_sold) AS total_qty,
            SUM(ds.revenue) AS total_revenue
        FROM daily_sales ds
        GROUP BY ds.org_id, ds.region, ds.sale_date;
    """)

    # v_inventory_status: current stock + classification
    op.execute("""
        CREATE OR REPLACE VIEW v_inventory_status AS
        SELECT
            i.org_id,
            i.product_id,
            p.sku,
            p.name AS product_name,
            c.name AS category_name,
            i.stock_on_hand,
            i.reorder_point,
            i.lead_time_days,
            i.unit_cost,
            i.holding_cost_pct,
            CASE
                WHEN i.stock_on_hand <= 0 THEN 'out_of_stock'
                WHEN i.stock_on_hand <= i.reorder_point THEN 'low_stock'
                WHEN i.stock_on_hand > i.reorder_point * 3 THEN 'overstock'
                ELSE 'healthy'
            END AS status_label
        FROM inventory i
        JOIN products p ON p.id = i.product_id
        LEFT JOIN categories c ON c.id = p.category_id;
    """)

    # ── Read-only role for NL2SQL ────────────────────────
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'bi_readonly') THEN
                CREATE ROLE bi_readonly NOLOGIN;
            END IF;
        END
        $$;
    """)
    op.execute("GRANT USAGE ON SCHEMA public TO bi_readonly;")
    op.execute(
        "GRANT SELECT ON v_kpi_daily, v_sales_by_product, v_sales_by_region, v_inventory_status TO bi_readonly;"
    )


def downgrade() -> None:
    # Drop views
    op.execute("DROP VIEW IF EXISTS v_inventory_status;")
    op.execute("DROP VIEW IF EXISTS v_sales_by_region;")
    op.execute("DROP VIEW IF EXISTS v_sales_by_product;")
    op.execute("DROP VIEW IF EXISTS v_kpi_daily;")

    # Revoke and drop role
    op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM bi_readonly;")
    op.execute("DROP ROLE IF EXISTS bi_readonly;")

    # Drop tables in reverse dependency order
    op.drop_table("audit_log")
    op.drop_table("reports")
    op.drop_table("recommendations")
    op.drop_table("alerts")
    op.drop_table("anomalies")
    op.drop_table("forecasts")
    op.drop_table("daily_sales")
    op.drop_table("inventory")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("customers")
    op.drop_table("products")
    op.drop_table("categories")
    op.drop_table("users")
    op.drop_table("orgs")
