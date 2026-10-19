"""
Seed script — loads the UCI Online Retail II dataset, cleans it, and populates
the database with real transactional data + SYNTHETIC inventory parameters.

Usage:
    python -m data.seed              # full seed
    python -m data.seed --synthetic  # synthetic inventory only (skip download)

Data source:
    UCI Online Retail II — https://archive.ics.uci.edu/dataset/502/online+retail+ii
    Falls back to generating a fully synthetic dataset if download fails.

⚠️  Inventory, lead-time, and cost data are SYNTHETIC.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# ── Setup ────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_FILE = DATA_DIR / "online_retail_ii.parquet"

# We read DATABASE_URL_SYNC from env (or fallback for local dev)
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg2://quantitext:changeme_dev_only@localhost:5432/quantitext",
)

# Deterministic UUIDs from strings (for idempotent seeding)
NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def stable_uuid(name: str) -> uuid.UUID:
    """Generate a deterministic UUID5 from a name — makes seeding idempotent."""
    return uuid.uuid5(NAMESPACE, name)


# ── Download / Cache ────────────────────────────────────

def download_retail_data() -> pd.DataFrame:
    """Download UCI Online Retail II or fall back to synthetic generation."""
    if CACHE_FILE.exists():
        try:
            log.info("Loading cached dataset from %s", CACHE_FILE)
            return pd.read_parquet(CACHE_FILE)
        except Exception as e:
            log.warning("Could not read parquet cache (%s).", e)

    log.info("Attempting to download UCI Online Retail II dataset...")
    try:
        # The dataset is available as Excel from UCI
        url = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
        import io
        import zipfile

        import httpx

        response = httpx.get(url, timeout=60, follow_redirects=True)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            # Find the Excel file inside the zip
            xlsx_files = [f for f in z.namelist() if f.endswith(".xlsx")]
            if not xlsx_files:
                raise FileNotFoundError("No .xlsx file found in archive")

            with z.open(xlsx_files[0]) as f:
                df = pd.read_excel(f, engine="openpyxl")

        log.info("Downloaded %d rows", len(df))
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            df.to_parquet(CACHE_FILE)
        except Exception as pe:
            log.warning("Could not write parquet cache (%s). Continuing.", pe)
        return df

    except Exception as e:
        log.warning("Download failed (%s). Generating synthetic retail data instead.", e)
        return generate_synthetic_retail_data()


def generate_synthetic_retail_data() -> pd.DataFrame:
    """Generate a fully synthetic retail dataset when UCI download fails."""
    log.info("Generating synthetic retail dataset (~50k rows)...")
    rng = np.random.default_rng(42)

    n_products = 200
    n_customers = 500
    n_orders = 8000

    # Products
    categories = ["Electronics", "Clothing", "Home & Garden", "Books", "Sports", "Food & Drink"]
    product_names = [f"Product-{i:04d}" for i in range(n_products)]
    product_categories = rng.choice(categories, n_products)
    product_prices = np.round(rng.uniform(1.0, 150.0, n_products), 2)

    # Customers
    countries = ["United Kingdom", "France", "Germany", "Spain", "Netherlands",
                 "Belgium", "Australia", "Japan", "United States", "India"]
    country_weights = [0.45, 0.10, 0.10, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05]
    customer_countries = rng.choice(countries, n_customers, p=country_weights)

    # Region mapping
    region_map = {
        "United Kingdom": "Europe", "France": "Europe", "Germany": "Europe",
        "Spain": "Europe", "Netherlands": "Europe", "Belgium": "Europe",
        "Australia": "Asia-Pacific", "Japan": "Asia-Pacific",
        "United States": "Americas", "India": "Asia-Pacific",
    }

    # Generate orders over ~2 years
    start_date = datetime(2022, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
    date_range_days = (end_date - start_date).days

    rows = []
    invoice_counter = 489000
    for _ in range(n_orders):
        invoice_counter += 1
        cust_idx = rng.integers(0, n_customers)
        order_date = start_date + timedelta(days=int(rng.integers(0, date_range_days)))
        n_items = int(rng.integers(1, 8))

        for _ in range(n_items):
            prod_idx = int(rng.integers(0, n_products))
            qty = int(rng.integers(1, 25))
            price = product_prices[prod_idx]

            rows.append({
                "Invoice": str(invoice_counter),
                "StockCode": f"SKU-{prod_idx:04d}",
                "Description": product_names[prod_idx],
                "Quantity": qty,
                "InvoiceDate": order_date,
                "Price": price,
                "Customer ID": float(cust_idx + 12000),
                "Country": customer_countries[cust_idx],
                "Category": product_categories[prod_idx],
                "Region": region_map[customer_countries[cust_idx]],
            })

    df = pd.DataFrame(rows)
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(CACHE_FILE)
    except Exception as pe:
        log.warning("Could not write parquet cache (%s). Continuing.", pe)
    log.info("Generated %d rows across %d orders", len(df), n_orders)
    return df


# ── Cleaning ────────────────────────────────────────────

def clean_retail_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the raw dataset: remove dupes, nulls, negatives, fix types."""
    original_len = len(df)

    # Standardise column names
    col_map = {}
    for col in df.columns:
        lower = col.strip().lower().replace(" ", "_")
        if "invoice" in lower and "date" not in lower:
            col_map[col] = "invoice"
        elif "invoice" in lower and "date" in lower:
            col_map[col] = "invoice_date"
        elif "stock" in lower or "code" in lower:
            col_map[col] = "stock_code"
        elif "description" in lower:
            col_map[col] = "description"
        elif "quantity" in lower:
            col_map[col] = "quantity"
        elif "price" in lower:
            col_map[col] = "price"
        elif "customer" in lower:
            col_map[col] = "customer_id"
        elif "country" in lower:
            col_map[col] = "country"
        elif "category" in lower:
            col_map[col] = "category"
        elif "region" in lower:
            col_map[col] = "region"

    df = df.rename(columns=col_map)

    # Drop rows with missing critical fields
    critical = ["invoice", "stock_code", "quantity", "price", "invoice_date"]
    existing_critical = [c for c in critical if c in df.columns]
    df = df.dropna(subset=existing_critical)

    # Remove cancellations (invoices starting with 'C')
    df = df[~df["invoice"].astype(str).str.startswith("C")]

    # Remove zero/negative prices and quantities
    df = df[(df["quantity"] > 0) & (df["price"] > 0)]

    # Remove duplicates
    df = df.drop_duplicates()

    # Ensure datetime
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], utc=True)

    # Fill missing customer IDs
    if "customer_id" in df.columns:
        df["customer_id"] = df["customer_id"].fillna(0).astype(int).astype(str)
    else:
        df["customer_id"] = "unknown"

    # Fill missing country
    if "country" not in df.columns:
        df["country"] = "Unknown"
    df["country"] = df["country"].fillna("Unknown")

    # Generate region from country if not present
    region_map = {
        "United Kingdom": "Europe", "France": "Europe", "Germany": "Europe",
        "EIRE": "Europe", "Spain": "Europe", "Netherlands": "Europe",
        "Belgium": "Europe", "Switzerland": "Europe", "Portugal": "Europe",
        "Italy": "Europe", "Finland": "Europe", "Austria": "Europe",
        "Norway": "Europe", "Denmark": "Europe", "Sweden": "Europe",
        "Australia": "Asia-Pacific", "Japan": "Asia-Pacific",
        "Singapore": "Asia-Pacific", "Hong Kong": "Asia-Pacific",
        "India": "Asia-Pacific",
        "United States": "Americas", "USA": "Americas",
        "Canada": "Americas", "Brazil": "Americas",
    }
    if "region" not in df.columns:
        df["region"] = df["country"].map(region_map).fillna("Other")

    # Generate category if not present (group by first char of stock_code)
    if "category" not in df.columns:
        df["category"] = df["stock_code"].str[:2].map(
            lambda x: f"Category-{x}" if isinstance(x, str) else "Uncategorized"
        )

    # Add line total
    df["line_total"] = (df["quantity"] * df["price"]).round(2)

    log.info("Cleaned: %d → %d rows (removed %d)", original_len, len(df), original_len - len(df))
    return df


# ── Database Seeding ────────────────────────────────────

def seed_database(df: pd.DataFrame) -> None:
    """Insert cleaned data into the database."""
    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        # ── Check if already seeded ──────────────────────
        result = session.execute(text("SELECT COUNT(*) FROM orgs"))
        if result.scalar() > 0:
            log.warning("Database already seeded. Drop tables first to re-seed.")
            log.info("To re-seed: alembic downgrade base && alembic upgrade head && python -m data.seed")
            return

        log.info("Seeding database...")

        # ── Org ──────────────────────────────────────────
        org_id = stable_uuid("demo-org")
        session.execute(
            text("""
                INSERT INTO orgs (id, name, slug, description, settings)
                VALUES (:id, :name, :slug, :desc, :settings)
            """),
            {
                "id": str(org_id), "name": "Demo Retail Co.",
                "slug": "demo-retail", "desc": "Synthetic demo organization",
                "settings": "{}",
            },
        )
        log.info("Created org: Demo Retail Co.")

        # ── Admin user (password: admin123 — dev only) ───
        admin_id = stable_uuid("admin-user")
        # Valid argon2 hash of 'admin123'
        try:
            from app.core.security import hash_password
            hashed = hash_password("admin123")
        except Exception:
            hashed = "$argon2id$v=19$m=65536,t=3,p=4$aos+yPaeP1sTX2QTmi7l1w$uVbhovRHYTukKXwM+PFN3IzJblUzXMPgORaxFYdaHC4"
        session.execute(
            text("""
                INSERT INTO users (id, org_id, email, hashed_password, full_name, role, is_active)
                VALUES (:id, :org_id, :email, :hash, :name, :role, true)
            """),
            {
                "id": str(admin_id), "org_id": str(org_id),
                "email": "admin@demo.local", "hash": hashed,
                "name": "Admin User", "role": "admin",
            },
        )
        log.info("Created admin user: admin@demo.local")

        # ── Categories ──────────────────────────────────
        categories = df["category"].unique()
        cat_id_map = {}
        for cat_name in categories:
            cat_slug = cat_name.lower().replace(" ", "-").replace("&", "and")[:100]
            cat_id = stable_uuid(f"cat-{cat_name}")
            cat_id_map[cat_name] = cat_id
            session.execute(
                text("""
                    INSERT INTO categories (id, org_id, name, slug)
                    VALUES (:id, :org_id, :name, :slug)
                """),
                {"id": str(cat_id), "org_id": str(org_id), "name": cat_name, "slug": cat_slug},
            )
        log.info("Inserted %d categories", len(categories))

        # ── Products ─────────────────────────────────────
        products_df = df.groupby("stock_code").agg(
            description=("description", "first"),
            category=("category", "first"),
            price=("price", "median"),
        ).reset_index()

        prod_id_map = {}
        for _, row in products_df.iterrows():
            prod_id = stable_uuid(f"prod-{row['stock_code']}")
            prod_id_map[row["stock_code"]] = prod_id
            cat_id = cat_id_map.get(row["category"])
            session.execute(
                text("""
                    INSERT INTO products (id, org_id, category_id, sku, name, unit_price, is_active)
                    VALUES (:id, :org_id, :cat_id, :sku, :name, :price, true)
                """),
                {
                    "id": str(prod_id), "org_id": str(org_id),
                    "cat_id": str(cat_id) if cat_id else None,
                    "sku": str(row["stock_code"])[:100],
                    "name": str(row["description"] or row["stock_code"])[:500],
                    "price": float(round(row["price"], 2)),
                },
            )
        log.info("Inserted %d products", len(products_df))

        # ── Customers ────────────────────────────────────
        customers_df = df.groupby("customer_id").agg(
            country=("country", "first"),
            region=("region", "first"),
        ).reset_index()

        cust_id_map = {}
        for _, row in customers_df.iterrows():
            cust_id = stable_uuid(f"cust-{row['customer_id']}")
            cust_id_map[str(row["customer_id"])] = cust_id
            session.execute(
                text("""
                    INSERT INTO customers (id, org_id, customer_code, country, region)
                    VALUES (:id, :org_id, :code, :country, :region)
                """),
                {
                    "id": str(cust_id), "org_id": str(org_id),
                    "code": str(row["customer_id"])[:100],
                    "country": str(row["country"])[:100],
                    "region": str(row["region"])[:100],
                },
            )
        log.info("Inserted %d customers", len(customers_df))

        # ── Orders + Order Items ─────────────────────────
        orders_df = df.groupby("invoice").agg(
            invoice_date=("invoice_date", "first"),
            customer_id=("customer_id", "first"),
            total=("line_total", "sum"),
        ).reset_index()

        order_count = 0
        item_count = 0
        for _, order_row in orders_df.iterrows():
            order_id = stable_uuid(f"order-{order_row['invoice']}")
            cust_id = cust_id_map.get(str(order_row["customer_id"]))

            session.execute(
                text("""
                    INSERT INTO orders (id, org_id, customer_id, invoice_no, invoice_date, total_amount)
                    VALUES (:id, :org_id, :cust_id, :inv_no, :inv_date, :total)
                """),
                {
                    "id": str(order_id), "org_id": str(org_id),
                    "cust_id": str(cust_id) if cust_id else None,
                    "inv_no": str(order_row["invoice"])[:50],
                    "inv_date": order_row["invoice_date"],
                    "total": float(round(order_row["total"], 2)),
                },
            )
            order_count += 1

            # Insert order items
            items = df[df["invoice"] == order_row["invoice"]]
            for _, item_row in items.iterrows():
                item_id = stable_uuid(f"item-{order_row['invoice']}-{item_row['stock_code']}-{item_count}")
                prod_id = prod_id_map.get(item_row["stock_code"])
                session.execute(
                    text("""
                        INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, line_total)
                        VALUES (:id, :order_id, :prod_id, :qty, :price, :total)
                    """),
                    {
                        "id": str(item_id), "order_id": str(order_id),
                        "prod_id": str(prod_id) if prod_id else None,
                        "qty": int(item_row["quantity"]),
                        "price": float(round(item_row["price"], 2)),
                        "total": float(round(item_row["line_total"], 2)),
                    },
                )
                item_count += 1

            # Commit in batches of 500 orders
            if order_count % 500 == 0:
                session.commit()
                log.info("  ... committed %d orders, %d items", order_count, item_count)

        session.commit()
        log.info("Inserted %d orders with %d line items", order_count, item_count)

        # ── Daily Sales (pre-aggregated) ─────────────────
        daily = df.groupby(
            [df["invoice_date"].dt.date, "stock_code", "region"]
        ).agg(
            quantity_sold=("quantity", "sum"),
            revenue=("line_total", "sum"),
        ).reset_index()
        daily.columns = ["sale_date", "stock_code", "region", "quantity_sold", "revenue"]

        ds_count = 0
        for _, row in daily.iterrows():
            prod_id = prod_id_map.get(row["stock_code"])
            if not prod_id:
                continue
            ds_id = stable_uuid(f"ds-{row['sale_date']}-{row['stock_code']}-{row['region']}")
            session.execute(
                text("""
                    INSERT INTO daily_sales (id, org_id, product_id, sale_date, quantity_sold, revenue, region)
                    VALUES (:id, :org_id, :prod_id, :sale_date, :qty, :rev, :region)
                """),
                {
                    "id": str(ds_id), "org_id": str(org_id),
                    "prod_id": str(prod_id),
                    "sale_date": row["sale_date"],
                    "qty": int(row["quantity_sold"]),
                    "rev": float(round(row["revenue"], 2)),
                    "region": str(row["region"])[:100],
                },
            )
            ds_count += 1
            if ds_count % 5000 == 0:
                session.commit()
                log.info("  ... committed %d daily_sales rows", ds_count)

        session.commit()
        log.info("Inserted %d daily_sales rows", ds_count)

        # ── Synthetic Inventory (CLEARLY MARKED) ─────────
        log.info("Generating SYNTHETIC inventory data...")
        rng = np.random.default_rng(42)

        for sku, prod_id in prod_id_map.items():
            # Synthetic parameters — do NOT present as real data
            stock = int(rng.integers(0, 500))
            lead_time = int(rng.choice([3, 5, 7, 10, 14, 21, 30]))
            unit_cost = round(float(rng.uniform(0.5, 80.0)), 2)
            moq = int(rng.choice([1, 5, 10, 25, 50, 100]))
            holding_pct = round(float(rng.uniform(0.10, 0.35)), 4)
            reorder_pt = int(rng.integers(10, 100))

            inv_id = stable_uuid(f"inv-{sku}")
            session.execute(
                text("""
                    INSERT INTO inventory (id, org_id, product_id, stock_on_hand, reorder_point,
                                           lead_time_days, min_order_qty, unit_cost, holding_cost_pct)
                    VALUES (:id, :org_id, :prod_id, :stock, :reorder, :lead, :moq, :cost, :holding)
                """),
                {
                    "id": str(inv_id), "org_id": str(org_id),
                    "prod_id": str(prod_id),
                    "stock": stock, "reorder": reorder_pt,
                    "lead": lead_time, "moq": moq,
                    "cost": unit_cost, "holding": holding_pct,
                },
            )

        session.commit()
        log.info("Inserted %d SYNTHETIC inventory records", len(prod_id_map))

        # ── Verify views ────────────────────────────────
        for view in ["v_kpi_daily", "v_sales_by_product", "v_sales_by_region", "v_inventory_status"]:
            result = session.execute(text(f"SELECT COUNT(*) FROM {view}"))  # noqa: S608
            count = result.scalar()
            log.info("View %s: %d rows", view, count)

        log.info("✅ Seed complete!")


# ── Main ────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the QuantiText database")
    parser.add_argument("--synthetic", action="store_true", help="Skip download, use fully synthetic data")
    args = parser.parse_args()

    if args.synthetic:
        df = generate_synthetic_retail_data()
    else:
        df = download_retail_data()

    df = clean_retail_data(df)
    seed_database(df)


if __name__ == "__main__":
    main()
