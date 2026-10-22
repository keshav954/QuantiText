"""
Seed script — loads the UCI Online Retail II dataset, cleans it, and populates
the database with real transactional data + SYNTHETIC inventory parameters,
anomalies, alerts, forecasts, closed-loop recommendations, reports, and feedback.

Usage:
    python -m data.seed              # full seed
    python -m data.seed --synthetic  # synthetic retail dataset (skip download)
    python -m data.seed --reset      # wipe existing data and reseed fresh

Data source:
    UCI Online Retail II — https://archive.ics.uci.edu/dataset/502/online+retail+ii
    Falls back to generating a fully synthetic dataset if download fails.

⚠️  Inventory, lead-time, forecasts, anomalies, recommendations, and cost data are SYNTHETIC.
"""

from __future__ import annotations

import argparse
import json
import logging
import uuid
from datetime import UTC, date, datetime, timedelta
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

# ── Download / Cache ────────────────────────────────────


def download_retail_data(years: int = 5) -> pd.DataFrame:
    """Download UCI Online Retail II or fall back to synthetic generation (5-year historical depth)."""
    min_required_days = int(years * 365) - 30

    if CACHE_FILE.exists():
        try:
            log.info("Checking cached dataset from %s", CACHE_FILE)
            cached_df = pd.read_parquet(CACHE_FILE)
            date_col = next((c for c in cached_df.columns if "date" in c.lower()), None)
            if date_col:
                dates = pd.to_datetime(cached_df[date_col], utc=True)
                span_days = (dates.max() - dates.min()).days
                if span_days >= min_required_days:
                    log.info(
                        "Cached dataset covers %d days (>= %d years). Reusing.",
                        span_days,
                        years,
                    )
                    return cached_df
                log.info(
                    "Cached dataset only covers %d days (< %d years). Regenerating %d-year dataset...",
                    span_days,
                    years,
                    years,
                )
            else:
                log.info(
                    "No date column in cached dataset. Regenerating %d-year dataset...",
                    years,
                )
        except Exception as e:  # noqa: BLE001
            log.warning("Could not inspect parquet cache (%s).", e)

    log.info("Attempting to download UCI Online Retail II dataset...")
    try:
        url = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
        import io
        import zipfile

        import httpx

        response = httpx.get(url, timeout=60, follow_redirects=True)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            xlsx_files = [f for f in z.namelist() if f.endswith(".xlsx")]
            if not xlsx_files:
                raise FileNotFoundError("No .xlsx file found in archive")

            with z.open(xlsx_files[0]) as f:
                df = pd.read_excel(f, engine="openpyxl")

        log.info("Downloaded UCI dataset with %d rows", len(df))
        # Note: UCI dataset is ~2 years (2009-2011). If 5 years requested, generate 5-year synthetic dataset.
        date_col = next((c for c in df.columns if "date" in c.lower()), None)
        if date_col:
            dates = pd.to_datetime(df[date_col], utc=True)
            span_days = (dates.max() - dates.min()).days
            if span_days < min_required_days:
                log.info(
                    "UCI dataset only covers %d days (< %d years). Generating full %d-year synthetic dataset.",
                    span_days,
                    years,
                    years,
                )
                return generate_synthetic_retail_data(years=years)

        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            df.to_parquet(CACHE_FILE)
        except Exception as pe:  # noqa: BLE001
            log.warning("Could not write parquet cache (%s). Continuing.", pe)
        return df

    except Exception as e:  # noqa: BLE001
        log.warning(
            "Download failed (%s). Generating %d-year synthetic retail data instead.",
            e,
            years,
        )
        return generate_synthetic_retail_data(years=years)


def generate_synthetic_retail_data(
    years: int = 5, n_orders: int = 25000
) -> pd.DataFrame:
    """Generate a fully synthetic retail dataset anchored dynamically up to today over N years."""
    date_range_days = int(years * 365.25)
    log.info(
        "Generating synthetic retail dataset (%d years = %d days, ~%d orders)...",
        years,
        date_range_days,
        n_orders,
    )
    rng = np.random.default_rng(42)

    n_products = 200
    n_customers = 500

    # Products
    categories = [
        "Electronics",
        "Clothing",
        "Home & Garden",
        "Books",
        "Sports",
        "Food & Drink",
    ]
    product_names = [f"Product-{i:04d}" for i in range(n_products)]
    product_categories = rng.choice(categories, n_products)
    product_prices = np.round(rng.uniform(1.0, 150.0, n_products), 2)

    # Customers
    countries = [
        "United Kingdom",
        "France",
        "Germany",
        "Spain",
        "Netherlands",
        "Belgium",
        "Australia",
        "Japan",
        "United States",
        "India",
    ]
    country_weights = [0.45, 0.10, 0.10, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05]
    customer_countries = rng.choice(countries, n_customers, p=country_weights)

    # Region mapping
    region_map = {
        "United Kingdom": "Europe",
        "France": "Europe",
        "Germany": "Europe",
        "Spain": "Europe",
        "Netherlands": "Europe",
        "Belgium": "Europe",
        "Australia": "Asia-Pacific",
        "Japan": "Asia-Pacific",
        "United States": "Americas",
        "India": "Asia-Pacific",
    }

    # Anchor orders dynamically up to today
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=date_range_days)

    # Compute probability weights for each day to simulate realistic yearly growth and seasonal peaks
    weights = np.zeros(date_range_days)
    month_seasonality = {
        1: 0.82,
        2: 0.85,
        3: 0.95,
        4: 1.00,
        5: 1.05,
        6: 1.10,
        7: 1.15,
        8: 1.05,
        9: 1.00,
        10: 1.12,
        11: 1.45,
        12: 1.70,  # Q4 holiday surges
    }

    for d in range(date_range_days):
        current_dt = start_date + timedelta(days=d)
        # 12% annual organic business expansion
        year_progress = d / 365.25
        growth_factor = (1.0 + 0.12) ** year_progress
        season_factor = month_seasonality.get(current_dt.month, 1.0)
        dow_factor = 1.08 if current_dt.weekday() < 5 else 0.88
        weights[d] = growth_factor * season_factor * dow_factor

    weights /= weights.sum()

    # Sample order days based on the distribution
    sampled_day_offsets = rng.choice(date_range_days, size=n_orders, p=weights)

    rows = []
    invoice_counter = 489000
    for order_idx in range(n_orders):
        invoice_counter += 1
        cust_idx = int(rng.integers(0, n_customers))
        day_offset = int(sampled_day_offsets[order_idx])
        hour = int(rng.integers(8, 22))
        minute = int(rng.integers(0, 60))
        order_date = start_date + timedelta(days=day_offset, hours=hour, minutes=minute)

        n_items = int(rng.integers(1, 8))
        for _ in range(n_items):
            prod_idx = int(rng.integers(0, n_products))
            qty = int(rng.integers(1, 25))
            price = product_prices[prod_idx]

            rows.append(
                {
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
                }
            )

    df = pd.DataFrame(rows)
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(CACHE_FILE)
        log.info(
            "Saved %d-year retail dataset (%d rows, %d orders) to %s",
            years,
            len(df),
            n_orders,
            CACHE_FILE,
        )
    except Exception as pe:  # noqa: BLE001
        log.warning("Could not write parquet cache (%s). Continuing.", pe)
    log.info(
        "Generated %d rows across %d orders spanning %d years (%s to %s)",
        len(df),
        n_orders,
        years,
        start_date.date(),
        end_date.date(),
    )
    return df


# ── Cleaning ────────────────────────────────────────────


def clean_retail_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the raw dataset: remove dupes, nulls, negatives, fix types, shift dates to today."""
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

    # Shift dates so the newest date is right now (ensures dashboard is never stale)
    max_date = df["invoice_date"].max()
    now_utc = datetime.now(UTC)
    if (now_utc - max_date).days > 1:
        delta = now_utc - max_date
        df["invoice_date"] = df["invoice_date"] + delta
        log.info(
            "Shifted dataset dates by %d days so newest orders align with today (%s)",
            delta.days,
            now_utc.date(),
        )

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
        "United Kingdom": "Europe",
        "France": "Europe",
        "Germany": "Europe",
        "EIRE": "Europe",
        "Spain": "Europe",
        "Netherlands": "Europe",
        "Belgium": "Europe",
        "Switzerland": "Europe",
        "Portugal": "Europe",
        "Italy": "Europe",
        "Finland": "Europe",
        "Austria": "Europe",
        "Norway": "Europe",
        "Denmark": "Europe",
        "Sweden": "Europe",
        "Australia": "Asia-Pacific",
        "Japan": "Asia-Pacific",
        "Singapore": "Asia-Pacific",
        "Hong Kong": "Asia-Pacific",
        "India": "Asia-Pacific",
        "United States": "Americas",
        "USA": "Americas",
        "Canada": "Americas",
        "Brazil": "Americas",
    }
    if "region" not in df.columns:
        df["region"] = df["country"].map(region_map).fillna("Other")

    # Generate category if not present
    if "category" not in df.columns:
        df["category"] = (
            df["stock_code"]
            .str[:2]
            .map(lambda x: f"Category-{x}" if isinstance(x, str) else "Uncategorized")
        )

    # Add line total
    df["line_total"] = (df["quantity"] * df["price"]).round(2)

    log.info(
        "Cleaned: %d → %d rows (removed %d)",
        original_len,
        len(df),
        original_len - len(df),
    )
    return df


# ── Database Seeding ────────────────────────────────────


def seed_database(df: pd.DataFrame, reset: bool = False) -> None:
    """Insert cleaned data into the database along with ML artifacts and decision records."""
    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        # ── Check if already seeded ──────────────────────
        result = session.execute(text("SELECT COUNT(*) FROM orgs"))
        count = result.scalar()
        if count > 0:
            if not reset:
                log.warning(
                    "Database already seeded (%d orgs found). Use --reset to wipe and reseed.",
                    count,
                )
                return
            log.info("Resetting existing database tables via TRUNCATE CASCADE...")
            session.execute(text("TRUNCATE TABLE orgs CASCADE;"))
            session.commit()
            log.info("Database wiped cleanly.")

        log.info("Seeding database...")

        # ── Org ──────────────────────────────────────────
        org_id = stable_uuid("demo-org")
        session.execute(
            text("""
                INSERT INTO orgs (id, name, slug, description, settings)
                VALUES (:id, :name, :slug, :desc, :settings)
            """),
            {
                "id": str(org_id),
                "name": "Demo Retail Co.",
                "slug": "demo-retail",
                "desc": "Synthetic demo organization",
                "settings": "{}",
            },
        )
        log.info("Created org: Demo Retail Co.")

        # ── Admin user (password: admin123 — dev only) ───
        admin_id = stable_uuid("admin-user")
        try:
            from app.core.security import hash_password

            hashed = hash_password("admin123")
        except Exception:  # noqa: BLE001
            hashed = "$argon2id$v=19$m=65536,t=3,p=4$aos+yPaeP1sTX2QTmi7l1w$uVbhovRHYTukKXwM+PFN3IzJblUzXMPgORaxFYdaHC4"
        session.execute(
            text("""
                INSERT INTO users (id, org_id, email, hashed_password, full_name, role, is_active)
                VALUES (:id, :org_id, :email, :hash, :name, :role, true)
            """),
            {
                "id": str(admin_id),
                "org_id": str(org_id),
                "email": "admin@demo.local",
                "hash": hashed,
                "name": "Admin User",
                "role": "admin",
            },
        )
        log.info("Created admin user: admin@demo.local (password: admin123)")

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
                {
                    "id": str(cat_id),
                    "org_id": str(org_id),
                    "name": cat_name,
                    "slug": cat_slug,
                },
            )
        log.info("Inserted %d categories", len(categories))

        # ── Products ─────────────────────────────────────
        products_df = (
            df.groupby("stock_code")
            .agg(
                description=("description", "first"),
                category=("category", "first"),
                price=("price", "median"),
            )
            .reset_index()
        )

        prod_id_map = {}
        prod_sku_list = []
        for _, row in products_df.iterrows():
            prod_id = stable_uuid(f"prod-{row['stock_code']}")
            prod_id_map[row["stock_code"]] = prod_id
            prod_sku_list.append(
                (row["stock_code"], prod_id, row["description"] or row["stock_code"])
            )
            cat_id = cat_id_map.get(row["category"])
            session.execute(
                text("""
                    INSERT INTO products (id, org_id, category_id, sku, name, unit_price, is_active)
                    VALUES (:id, :org_id, :cat_id, :sku, :name, :price, true)
                """),
                {
                    "id": str(prod_id),
                    "org_id": str(org_id),
                    "cat_id": str(cat_id) if cat_id else None,
                    "sku": str(row["stock_code"])[:100],
                    "name": str(row["description"] or row["stock_code"])[:500],
                    "price": float(round(row["price"], 2)),
                },
            )
        log.info("Inserted %d products", len(products_df))

        # ── Customers ────────────────────────────────────
        customers_df = (
            df.groupby("customer_id")
            .agg(
                country=("country", "first"),
                region=("region", "first"),
            )
            .reset_index()
        )

        cust_id_map = {}
        cust_id_list = []
        for _, row in customers_df.iterrows():
            cust_id = stable_uuid(f"cust-{row['customer_id']}")
            cust_id_map[str(row["customer_id"])] = cust_id
            cust_id_list.append(cust_id)
            session.execute(
                text("""
                    INSERT INTO customers (id, org_id, customer_code, country, region)
                    VALUES (:id, :org_id, :code, :country, :region)
                """),
                {
                    "id": str(cust_id),
                    "org_id": str(org_id),
                    "code": str(row["customer_id"])[:100],
                    "country": str(row["country"])[:100],
                    "region": str(row["region"])[:100],
                },
            )
        log.info("Inserted %d customers", len(customers_df))

        # ── Orders + Order Items ─────────────────────────
        orders_df = (
            df.groupby("invoice")
            .agg(
                invoice_date=("invoice_date", "first"),
                customer_id=("customer_id", "first"),
                total=("line_total", "sum"),
            )
            .reset_index()
        )

        log.info(
            "Batch inserting %d orders and %d line items...", len(orders_df), len(df)
        )
        orders_batch = []
        for _, order_row in orders_df.iterrows():
            order_id = stable_uuid(f"order-{order_row['invoice']}")
            cust_id = cust_id_map.get(str(order_row["customer_id"]))
            orders_batch.append(
                {
                    "id": str(order_id),
                    "org_id": str(org_id),
                    "cust_id": str(cust_id) if cust_id else None,
                    "inv_no": str(order_row["invoice"])[:50],
                    "inv_date": order_row["invoice_date"],
                    "total": float(round(order_row["total"], 2)),
                }
            )

        order_sql = text("""
            INSERT INTO orders (id, org_id, customer_id, invoice_no, invoice_date, total_amount)
            VALUES (:id, :org_id, :cust_id, :inv_no, :inv_date, :total)
        """)
        batch_size = 2000
        for i in range(0, len(orders_batch), batch_size):
            session.execute(order_sql, orders_batch[i : i + batch_size])
            session.commit()
            log.info(
                "  ... committed %d / %d orders",
                min(i + batch_size, len(orders_batch)),
                len(orders_batch),
            )

        # Insert order items
        items_batch = []
        for item_idx, item_row in df.iterrows():
            order_id = stable_uuid(f"order-{item_row['invoice']}")
            item_id = stable_uuid(
                f"item-{item_row['invoice']}-{item_row['stock_code']}-{item_idx}"
            )
            prod_id = prod_id_map.get(item_row["stock_code"])
            items_batch.append(
                {
                    "id": str(item_id),
                    "order_id": str(order_id),
                    "prod_id": str(prod_id) if prod_id else None,
                    "qty": int(item_row["quantity"]),
                    "price": float(round(item_row["price"], 2)),
                    "total": float(round(item_row["line_total"], 2)),
                }
            )

        item_sql = text("""
            INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, line_total)
            VALUES (:id, :order_id, :prod_id, :qty, :price, :total)
        """)
        for i in range(0, len(items_batch), batch_size):
            session.execute(item_sql, items_batch[i : i + batch_size])
            session.commit()
            log.info(
                "  ... committed %d / %d items",
                min(i + batch_size, len(items_batch)),
                len(items_batch),
            )

        log.info(
            "Inserted %d orders with %d line items", len(orders_batch), len(items_batch)
        )

        # ── Daily Sales (pre-aggregated) ─────────────────
        daily = (
            df.groupby([df["invoice_date"].dt.date, "stock_code", "region"])
            .agg(
                quantity_sold=("quantity", "sum"),
                revenue=("line_total", "sum"),
            )
            .reset_index()
        )
        daily.columns = [
            "sale_date",
            "stock_code",
            "region",
            "quantity_sold",
            "revenue",
        ]

        daily_batch = []
        for _, row in daily.iterrows():
            prod_id = prod_id_map.get(row["stock_code"])
            if not prod_id:
                continue
            ds_id = stable_uuid(
                f"ds-{row['sale_date']}-{row['stock_code']}-{row['region']}"
            )
            daily_batch.append(
                {
                    "id": str(ds_id),
                    "org_id": str(org_id),
                    "prod_id": str(prod_id),
                    "sale_date": row["sale_date"],
                    "qty": int(row["quantity_sold"]),
                    "rev": float(round(row["revenue"], 2)),
                    "region": str(row["region"])[:100],
                }
            )

        ds_sql = text("""
            INSERT INTO daily_sales (id, org_id, product_id, sale_date, quantity_sold, revenue, region)
            VALUES (:id, :org_id, :prod_id, :sale_date, :qty, :rev, :region)
        """)
        ds_batch_size = 5000
        for i in range(0, len(daily_batch), ds_batch_size):
            session.execute(ds_sql, daily_batch[i : i + ds_batch_size])
            session.commit()
            log.info(
                "  ... committed %d / %d daily_sales rows",
                min(i + ds_batch_size, len(daily_batch)),
                len(daily_batch),
            )

        log.info("Inserted %d daily_sales rows", len(daily_batch))

        # ── Synthetic Inventory (CLEARLY MARKED) ─────────
        log.info("Generating SYNTHETIC inventory data...")
        rng = np.random.default_rng(42)

        for sku, prod_id in prod_id_map.items():
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
                    "id": str(inv_id),
                    "org_id": str(org_id),
                    "prod_id": str(prod_id),
                    "stock": stock,
                    "reorder": reorder_pt,
                    "lead": lead_time,
                    "moq": moq,
                    "cost": unit_cost,
                    "holding": holding_pct,
                },
            )

        session.commit()
        log.info("Inserted %d SYNTHETIC inventory records", len(prod_id_map))

        # ── Anomalies & Alerts (Closed Loop demonstration) ───
        log.info("Generating demonstration anomalies and alerts...")
        today = date.today()
        now_dt = datetime.now(UTC)

        sample_products = prod_sku_list[:6]
        anomalies_data = [
            {
                "prod": sample_products[0],
                "type": "revenue_spike",
                "detector": "zscore",
                "severity": 0.88,
                "impact": 2450.00,
                "days_ago": 1,
                "details": {
                    "zscore": 3.82,
                    "baseline_revenue": 480.00,
                    "actual_revenue": 2930.00,
                    "cause": "Regional social media campaign surge",
                    "impact_pct": "+510%",
                },
                "alert_title": "Sudden Revenue Surge (+510%) on SKU",
                "alert_sev": "warning",
                "alert_desc": "High velocity spike detected in Europe region exceeding 3-sigma variance threshold.",
            },
            {
                "prod": sample_products[1],
                "type": "revenue_drop",
                "detector": "iforest",
                "severity": 0.94,
                "impact": -3800.00,
                "days_ago": 2,
                "details": {
                    "anomaly_score": -0.45,
                    "baseline_units": 75,
                    "actual_units": 6,
                    "cause": "Supplier component shortage causing stockout",
                    "impact_pct": "-92%",
                },
                "alert_title": "Severe Demand Drop & Stockout Threat",
                "alert_sev": "critical",
                "alert_desc": "Sales collapsed by 92% against trailing average. Current inventory insufficient to fulfill backorders.",
            },
            {
                "prod": sample_products[2],
                "type": "zero_sales",
                "detector": "data_quality",
                "severity": 0.62,
                "impact": -1100.00,
                "days_ago": 4,
                "details": {
                    "streak_days": 4,
                    "expected_daily_qty": 18,
                    "cause": "Catalog listing broken URL post-deployment",
                    "impact_pct": "-100%",
                },
                "alert_title": "Zero Sales Streak (4 Consecutive Days)",
                "alert_sev": "warning",
                "alert_desc": "Product recorded zero transactions over the past 4 days. Link inspection and catalog check advised.",
            },
            {
                "prod": sample_products[3],
                "type": "inventory_critical",
                "detector": "zscore",
                "severity": 0.81,
                "impact": -1950.00,
                "days_ago": 1,
                "details": {
                    "current_stock": 5,
                    "reorder_point": 50,
                    "days_of_stock": 0.6,
                    "cause": "Depletion rate 3x higher than forecast",
                    "impact_pct": "-90%",
                },
                "alert_title": "Critical Stock Outage Imminent (< 1 Day)",
                "alert_sev": "critical",
                "alert_desc": "Stock on hand fell to 5 units against reorder threshold of 50. Immediate replenishment needed.",
            },
            {
                "prod": sample_products[4],
                "type": "revenue_spike",
                "detector": "iforest",
                "severity": 0.55,
                "impact": 890.00,
                "days_ago": 3,
                "details": {
                    "anomaly_score": -0.22,
                    "baseline_revenue": 210.00,
                    "actual_revenue": 1100.00,
                    "cause": "B2B bulk purchase transaction",
                    "impact_pct": "+423%",
                },
                "alert_title": "Unusual B2B Bulk Order Spike",
                "alert_sev": "info",
                "alert_desc": "Unusually large single invoice recorded for enterprise client account.",
            },
        ]

        anomaly_ids = []
        for i, a in enumerate(anomalies_data):
            anom_id = stable_uuid(f"anom-{i}-{a['prod'][0]}")
            anomaly_ids.append(anom_id)
            det_date = today - timedelta(days=a["days_ago"])
            session.execute(
                text("""
                    INSERT INTO anomalies (id, org_id, product_id, detected_date, anomaly_type,
                                           detector, severity_score, estimated_impact, details, is_dismissed, created_at)
                    VALUES (:id, :org_id, :prod_id, :det_date, :anom_type, :detector,
                            :sev, :impact, :details, false, :created_at)
                """),
                {
                    "id": str(anom_id),
                    "org_id": str(org_id),
                    "prod_id": str(a["prod"][1]),
                    "det_date": det_date,
                    "anom_type": a["type"],
                    "detector": a["detector"],
                    "sev": a["severity"],
                    "impact": a["impact"],
                    "details": json.dumps(a["details"]),
                    "created_at": now_dt - timedelta(days=a["days_ago"]),
                },
            )

            # Linked Alert
            alert_id = stable_uuid(f"alert-{i}-{a['prod'][0]}")
            session.execute(
                text("""
                    INSERT INTO alerts (id, org_id, anomaly_id, title, description, severity, is_read, created_at)
                    VALUES (:id, :org_id, :anom_id, :title, :desc, :sev, false, :created_at)
                """),
                {
                    "id": str(alert_id),
                    "org_id": str(org_id),
                    "anom_id": str(anom_id),
                    "title": f"{a['alert_title']} [{a['prod'][0]}]",
                    "desc": a["alert_desc"],
                    "sev": a["alert_sev"],
                    "created_at": now_dt - timedelta(days=a["days_ago"]),
                },
            )

        # Standalone system info alert
        sys_alert_id = stable_uuid("alert-sys-info-01")
        session.execute(
            text("""
                INSERT INTO alerts (id, org_id, anomaly_id, title, description, severity, is_read, created_at)
                VALUES (:id, :org_id, NULL, :title, :desc, :sev, false, :created_at)
            """),
            {
                "id": str(sys_alert_id),
                "org_id": str(org_id),
                "title": "Machine Learning Pipelines Active (LightGBM & Prophet)",
                "desc": "Demand forecasting models updated across catalog. Average test MAPE: 7.8%.",
                "sev": "info",
                "created_at": now_dt,
            },
        )
        session.commit()
        log.info(
            "Inserted %d anomalies and %d alerts",
            len(anomalies_data),
            len(anomalies_data) + 1,
        )

        # ── Forecasts (Demonstration) ────────────────────
        log.info("Generating demonstration forecasts for top products...")
        forecast_count = 0
        for sku, prod_id, name in prod_sku_list[:12]:
            base_demand = float(rng.uniform(15.0, 50.0))
            for horizon in [7, 14, 30]:
                for day_offset in range(1, horizon + 1):
                    fc_date = today + timedelta(days=day_offset)
                    # Add mild seasonality
                    seasonal_factor = float(
                        1.0 + 0.15 * float(np.sin(day_offset / 3.5))
                    )
                    pred = float(
                        round(
                            base_demand * seasonal_factor + float(rng.normal(0, 2.0)), 2
                        )
                    )
                    lower = float(round(max(0.0, pred * 0.82), 2))
                    upper = float(round(pred * 1.22, 2))

                    fc_id = stable_uuid(f"fc-{sku}-{horizon}-{day_offset}")
                    session.execute(
                        text("""
                            INSERT INTO forecasts (id, org_id, product_id, forecast_date, horizon_days,
                                                   predicted_qty, lower_bound, upper_bound, model_name, mape, created_at)
                            VALUES (:id, :org_id, :prod_id, :fc_date, :horizon,
                                    :pred, :lower, :upper, :model, :mape, :created_at)
                        """),
                        {
                            "id": str(fc_id),
                            "org_id": str(org_id),
                            "prod_id": str(prod_id),
                            "fc_date": fc_date,
                            "horizon": int(horizon),
                            "pred": float(pred),
                            "lower": float(lower),
                            "upper": float(upper),
                            "model": "LightGBMForecaster",
                            "mape": 0.078,
                            "created_at": now_dt,
                        },
                    )
                    forecast_count += 1

        session.commit()
        log.info("Inserted %d forecast records across 12 products", forecast_count)

        # ── Recommendations (Closed-Loop Decision Support) ───
        log.info("Generating closed-loop recommendations...")
        recs_data = [
            {
                "sku": sample_products[1][0],
                "prod_id": sample_products[1][1],
                "action": "reorder",
                "reason": "Critical stockout threat on high-revenue SKU. Reorder 180 units immediately to avoid projected £3,800 stockout penalty.",
                "status": "pending",
                "params": {
                    "suggested_qty": 180,
                    "lead_time_days": 7,
                    "urgency": "immediate",
                    "estimated_cost": 2160.00,
                    "supplier": "Apex Distribution Ltd",
                },
                "approved_by": None,
                "decided_at": None,
            },
            {
                "sku": sample_products[0][0],
                "prod_id": sample_products[0][1],
                "action": "investigate",
                "reason": "Sustained +510% demand surge observed. Adjust safety stock buffer from 20 to 65 units to capture projected upside.",
                "status": "approved",
                "params": {
                    "safety_stock_current": 20,
                    "safety_stock_proposed": 65,
                    "revenue_opportunity": 2450.00,
                    "confidence": "95%",
                },
                "approved_by": str(admin_id),
                "decided_at": now_dt - timedelta(hours=8),
            },
            {
                "sku": sample_products[2][0],
                "prod_id": sample_products[2][1],
                "action": "markdown",
                "reason": "Zero sales streak for 4 days with 320 units idle in warehouse. Run 15% markdown campaign to clear inventory.",
                "status": "pending",
                "params": {
                    "discount_pct": 15,
                    "current_price": 32.00,
                    "promo_price": 27.20,
                    "estimated_recovery": 1400.00,
                },
                "approved_by": None,
                "decided_at": None,
            },
            {
                "sku": sample_products[3][0],
                "prod_id": sample_products[3][1],
                "action": "reorder",
                "reason": "Inventory at 5 units (<1 day of cover). Calculated EOQ order of 120 units based on replenishment schedule.",
                "status": "pending",
                "params": {
                    "suggested_qty": 120,
                    "lead_time_days": 10,
                    "urgency": "immediate",
                    "estimated_cost": 1540.00,
                },
                "approved_by": None,
                "decided_at": None,
            },
        ]

        for i, r in enumerate(recs_data):
            rec_id = stable_uuid(f"rec-{i}-{r['sku']}")
            session.execute(
                text("""
                    INSERT INTO recommendations (id, org_id, product_id, action_type, reason,
                                                 parameters, status, approved_by, decided_at, created_at)
                    VALUES (:id, :org_id, :prod_id, :action, :reason,
                            :params, :status, :approved_by, :decided_at, :created_at)
                """),
                {
                    "id": str(rec_id),
                    "org_id": str(org_id),
                    "prod_id": str(r["prod_id"]),
                    "action": r["action"],
                    "reason": r["reason"],
                    "params": json.dumps(r["params"]),
                    "status": r["status"],
                    "approved_by": r["approved_by"],
                    "decided_at": r["decided_at"],
                    "created_at": now_dt - timedelta(hours=12),
                },
            )
        session.commit()
        log.info("Inserted %d closed-loop recommendations", len(recs_data))

        # ── Reports (Executive BI Summaries) ─────────────────
        log.info("Generating demonstration reports...")
        report_agg = {
            "period": f"Trailing 30 days to {today}",
            "kpi_summary": {
                "total_revenue": 148250.00,
                "total_orders": 3120,
                "avg_order_value": 47.52,
                "unique_customers": 420,
                "revenue_trend": 0.124,
                "orders_trend": 0.082,
            },
            "top_products": [
                {"sku": p[0], "name": p[2], "total_revenue": 8450.00, "total_qty": 340}
                for p in sample_products[:5]
            ],
            "anomalies_summary": {
                "total_detected": len(anomalies_data),
                "critical": 2,
                "warnings": 2,
                "estimated_net_impact": -3210.00,
            },
        }

        report_narrative = (
            "## Executive Summary & Closed-Loop Analysis\n\n"
            "Over the trailing 30-day operating period, total retail revenue reached **£148,250.00** "
            "across 3,120 fulfillment orders, maintaining a healthy **12.4% MoM expansion** rate. "
            "Average Order Value (AOV) stood at **£47.52** with steady customer acquisition.\n\n"
            "### Anomaly & Root Cause Findings\n"
            "- **Viral Demand Spike (SKU-0000)**: A +510% revenue surge triggered Z-score anomaly detector. Root cause attributed to regional digital promotional exposure.\n"
            "- **Supply Bottleneck (SKU-0001)**: Isolation Forest flagged an acute 92% volume contraction caused by upstream distributor stockout.\n\n"
            "### AI Decision Support Actions\n"
            "- **Replenishment**: Recommended expedited purchase order of 180 units for critical SKU to avert £3,800 lost margin.\n"
            "- **Inventory Buffer**: Approved safety stock scaling from 20 to 65 units for high-velocity items.\n"
            "- **Slow-Mover Clearance**: Proposed 15% markdown to clear stagnant inventory.\n"
        )

        rep_id_1 = stable_uuid("report-weekly-01")
        session.execute(
            text("""
                INSERT INTO reports (id, org_id, generated_by, title, report_type,
                                     aggregated_data, narrative, file_path, created_at)
                VALUES (:id, :org_id, :gen_by, :title, :rep_type,
                        :agg, :narrative, NULL, :created_at)
            """),
            {
                "id": str(rep_id_1),
                "org_id": str(org_id),
                "gen_by": str(admin_id),
                "title": "Weekly Business Intelligence & Operations Review",
                "rep_type": "weekly",
                "agg": json.dumps(report_agg),
                "narrative": report_narrative,
                "created_at": now_dt - timedelta(days=2),
            },
        )

        rep_id_2 = stable_uuid("report-monthly-02")
        session.execute(
            text("""
                INSERT INTO reports (id, org_id, generated_by, title, report_type,
                                     aggregated_data, narrative, file_path, created_at)
                VALUES (:id, :org_id, :gen_by, :title, :rep_type,
                        :agg, :narrative, NULL, :created_at)
            """),
            {
                "id": str(rep_id_2),
                "org_id": str(org_id),
                "gen_by": str(admin_id),
                "title": "Monthly Closed-Loop Performance & Inventory Audit",
                "rep_type": "on_demand",
                "agg": json.dumps(report_agg),
                "narrative": report_narrative.replace("Weekly", "Monthly"),
                "created_at": now_dt - timedelta(days=9),
            },
        )
        session.commit()
        log.info("Inserted demonstration reports")

        # ── Customer Feedback (Hybrid RAG Demonstration) ───
        log.info("Generating demonstration customer feedback...")
        reviews = [
            (
                "review",
                5,
                "Outstanding product quality and lightning-fast next day delivery!",
                "positive",
                0.95,
                ["quality", "delivery"],
            ),
            (
                "review",
                4,
                "Item matches description accurately, packing could be slightly sturdier.",
                "positive",
                0.65,
                ["packaging", "accuracy"],
            ),
            (
                "support_ticket",
                1,
                "Delayed shipment, tracking number was not updating for 3 days.",
                "negative",
                -0.85,
                ["delivery", "tracking"],
            ),
            (
                "review",
                2,
                "Stock arrived with damaged exterior box, though item worked fine.",
                "negative",
                -0.45,
                ["packaging"],
            ),
            (
                "survey",
                5,
                "Very satisfied with pricing and repeat order experience.",
                "positive",
                0.90,
                ["price", "loyalty"],
            ),
            (
                "review",
                3,
                "Decent value for money, but customer service took 48 hours to answer inquiry.",
                "neutral",
                0.05,
                ["support", "price"],
            ),
            (
                "review",
                5,
                "Flawless finish! Exceeded expectations in every category.",
                "positive",
                0.98,
                ["quality"],
            ),
            (
                "support_ticket",
                2,
                "Received wrong color variation from ordered SKU.",
                "negative",
                -0.70,
                ["fulfillment", "accuracy"],
            ),
        ]

        fb_count = 0
        for i, (source, rating, text_content, sentiment, score, themes) in enumerate(
            reviews
        ):
            fb_id = stable_uuid(f"feedback-{i}")
            prod_tuple = sample_products[i % len(sample_products)]
            cust_id = cust_id_list[i % len(cust_id_list)] if cust_id_list else None
            session.execute(
                text("""
                    INSERT INTO customer_feedback (id, org_id, product_id, customer_id, source, rating,
                                                   text_content, sentiment, sentiment_score, themes,
                                                   region, feedback_date, created_at)
                    VALUES (:id, :org_id, :prod_id, :cust_id, :source, :rating,
                            :text, :sentiment, :score, :themes, :region, :fb_date, :created_at)
                """),
                {
                    "id": str(fb_id),
                    "org_id": str(org_id),
                    "prod_id": str(prod_tuple[1]),
                    "cust_id": str(cust_id) if cust_id else None,
                    "source": source,
                    "rating": rating,
                    "text": text_content,
                    "sentiment": sentiment,
                    "score": score,
                    "themes": json.dumps(themes),
                    "region": "Europe",
                    "fb_date": today - timedelta(days=i),
                    "created_at": now_dt - timedelta(days=i),
                },
            )
            fb_count += 1

        session.commit()
        log.info("Inserted %d customer feedback records", fb_count)

        # ── Verify views ────────────────────────────────
        for view in [
            "v_kpi_daily",
            "v_sales_by_product",
            "v_sales_by_region",
            "v_inventory_status",
        ]:
            result = session.execute(text(f"SELECT COUNT(*) FROM {view}"))
            count = result.scalar()
            log.info("View %s: %d rows", view, count)

        log.info(
            "✅ Database seed complete and verified! QuantiText is ready for presentation."
        )


# ── Main ────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the QuantiText database")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Skip download, use fully synthetic data",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Wipe existing tables and reseed from scratch",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="Number of years of historical data to generate (default: 5)",
    )
    args = parser.parse_args()

    if args.synthetic:
        df = generate_synthetic_retail_data(years=args.years)
    else:
        df = download_retail_data(years=args.years)

    df = clean_retail_data(df)
    seed_database(df, reset=args.reset)


if __name__ == "__main__":
    main()
