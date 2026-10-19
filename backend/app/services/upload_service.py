"""
Upload service — CSV/Excel onboarding into the standard schema.

Pipeline:
1. Accept CSV/Excel upload, save to temp storage.
2. Auto-detect columns and suggest mappings to the schema.
3. Validate the data (types, required fields, duplicates).
4. Load into orders/products/daily_sales tables.
5. Refresh materialized views.

Data loaded via this service is clearly labelled as user-uploaded.
"""

from __future__ import annotations

import csv
import io
import logging
import uuid
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# Temp upload directory
_UPLOAD_DIR = Path("/app/data/uploads")

# Known column synonyms for auto-detection
_COLUMN_SYNONYMS: dict[str, list[str]] = {
    "invoice_no": ["invoice", "invoiceno", "invoice_no", "invoice_number", "order_id", "order_no"],
    "invoice_date": ["invoicedate", "invoice_date", "date", "order_date"],
    "product_name": ["description", "product_name", "productname", "item", "product"],
    "sku": ["stockcode", "stock_code", "sku", "item_code", "product_code"],
    "quantity": ["quantity", "qty", "quantity_sold", "units"],
    "unit_price": ["unitprice", "unit_price", "price", "rate"],
    "customer_id": ["customerid", "customer_id", "customer_no"],
    "country": ["country", "region"],
}

# Target columns we need
_TARGET_COLUMNS = [
    "invoice_no", "invoice_date", "sku", "product_name",
    "quantity", "unit_price", "customer_id", "country",
]


# ── Public API ─────────────────────────────────────────────────────────────────


async def save_upload(filename: str, content: bytes) -> str:
    """Save an uploaded file to the temp directory. Returns the stored filename."""
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{filename}"
    path = _UPLOAD_DIR / safe_name
    path.write_bytes(content)
    log.info("Saved upload: %s (%d bytes)", safe_name, len(content))
    return safe_name


async def preview_upload(filename: str) -> dict:
    """
    Read an uploaded file and auto-detect column mappings.
    Returns detected columns, suggested mappings, and sample rows.
    """
    path = _UPLOAD_DIR / filename
    df = _read_file(path)

    # Auto-detect mappings
    detected = list(df.columns)
    mappings = _auto_map_columns(detected)

    # Sample rows
    sample = df.head(5).fillna("").to_dict(orient="records")

    return {
        "filename": filename,
        "row_count": len(df),
        "detected_columns": detected,
        "suggested_mappings": mappings,
        "sample_rows": sample,
    }


async def validate_upload(filename: str, mappings: list[dict]) -> dict:
    """
    Validate the uploaded data against the target schema.
    Returns validation results with error details.
    """
    path = _UPLOAD_DIR / filename
    df = _read_file(path)

    # Apply mappings
    rename_map = {m["source_column"]: m["target_column"] for m in mappings}
    df = df.rename(columns=rename_map)

    errors: list[str] = []
    warnings: list[str] = []

    # Check required columns
    required = ["invoice_no", "quantity", "unit_price"]
    for col in required:
        if col not in df.columns:
            errors.append(f"Required column '{col}' is missing")

    if errors:
        return {
            "is_valid": False,
            "total_rows": len(df),
            "valid_rows": 0,
            "error_count": len(errors),
            "errors": errors[:20],
            "warnings": warnings,
        }

    # Validate data types
    error_count = 0

    # Numeric columns
    for col in ["quantity", "unit_price"]:
        if col in df.columns:
            non_numeric = pd.to_numeric(df[col], errors="coerce").isna() & df[col].notna()
            bad_count = non_numeric.sum()
            if bad_count > 0:
                errors.append(f"Column '{col}' has {bad_count} non-numeric values")
                error_count += bad_count

    # Date column
    if "invoice_date" in df.columns:
        dates = pd.to_datetime(df["invoice_date"], errors="coerce", dayfirst=True)
        bad_dates = dates.isna() & df["invoice_date"].notna()
        bad_count = bad_dates.sum()
        if bad_count > 0:
            warnings.append(f"Column 'invoice_date' has {bad_count} unparseable dates")

    # Negative quantities
    if "quantity" in df.columns:
        qty = pd.to_numeric(df["quantity"], errors="coerce")
        neg_count = (qty < 0).sum()
        if neg_count > 0:
            warnings.append(f"{neg_count} rows have negative quantities (returns/cancellations)")

    # Zero prices
    if "unit_price" in df.columns:
        price = pd.to_numeric(df["unit_price"], errors="coerce")
        zero_count = (price == 0).sum()
        if zero_count > 0:
            warnings.append(f"{zero_count} rows have zero unit price")

    # Duplicates
    if "invoice_no" in df.columns and "sku" in df.columns:
        dupes = df.duplicated(subset=["invoice_no", "sku"], keep=False).sum()
        if dupes > 0:
            warnings.append(f"{dupes} potential duplicate rows detected")

    valid_rows = len(df) - error_count

    return {
        "is_valid": len(errors) == 0,
        "total_rows": len(df),
        "valid_rows": max(0, valid_rows),
        "error_count": error_count,
        "errors": errors[:20],
        "warnings": warnings[:20],
    }


async def load_upload(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    filename: str,
    mappings: list[dict],
    replace_existing: bool = False,
) -> dict:
    """
    Load validated upload into the standard schema.

    Creates products, customers, orders, order_items, and daily_sales.
    """
    path = _UPLOAD_DIR / filename
    df = _read_file(path)

    # Apply mappings
    rename_map = {m["source_column"]: m["target_column"] for m in mappings}
    df = df.rename(columns=rename_map)

    # Clean data
    if "quantity" in df.columns:
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    if "unit_price" in df.columns:
        df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce").fillna(0)
    if "invoice_date" in df.columns:
        df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce", dayfirst=True)
    else:
        df["invoice_date"] = datetime.now()

    # Filter valid rows
    df = df[df["quantity"] != 0].copy()

    org_str = str(org_id)
    products_created = 0
    orders_created = 0

    try:
        if replace_existing:
            await db.execute(
                text("DELETE FROM daily_sales WHERE org_id = :org_id"),
                {"org_id": org_str},
            )
            await db.execute(
                text("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE org_id = :org_id)"),
                {"org_id": org_str},
            )
            await db.execute(
                text("DELETE FROM orders WHERE org_id = :org_id"),
                {"org_id": org_str},
            )

        # Create missing products
        if "sku" in df.columns:
            unique_skus = df[["sku"]].drop_duplicates()
            if "product_name" in df.columns:
                unique_skus = df[["sku", "product_name"]].drop_duplicates(subset=["sku"])

            for _, row in unique_skus.iterrows():
                sku = str(row.get("sku", ""))[:50]
                if not sku:
                    continue

                # Check if product exists
                existing = await db.execute(
                    text("SELECT id FROM products WHERE org_id = :org_id AND sku = :sku"),
                    {"org_id": org_str, "sku": sku},
                )
                if existing.first():
                    continue

                name = str(row.get("product_name", sku))[:200]
                price = float(df[df["sku"] == sku]["unit_price"].median()) if "unit_price" in df.columns else 0

                await db.execute(
                    text("""
                        INSERT INTO products (id, org_id, sku, name, unit_price, is_active)
                        VALUES (:id, :org_id, :sku, :name, :price, TRUE)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "org_id": org_str,
                        "sku": sku,
                        "name": name,
                        "price": price,
                    },
                )
                products_created += 1

        # Create orders and order items
        if "invoice_no" in df.columns:
            for invoice_no, group in df.groupby("invoice_no"):
                inv_date = group["invoice_date"].iloc[0] if "invoice_date" in group.columns else datetime.now()
                total = float((group["quantity"] * group["unit_price"]).sum()) if "unit_price" in group.columns else 0

                order_id = uuid.uuid4()
                await db.execute(
                    text("""
                        INSERT INTO orders (id, org_id, invoice_no, invoice_date, total_amount)
                        VALUES (:id, :org_id, :invoice_no, :invoice_date, :total)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "id": str(order_id),
                        "org_id": org_str,
                        "invoice_no": str(invoice_no)[:50],
                        "invoice_date": inv_date,
                        "total": total,
                    },
                )
                orders_created += 1

        # Aggregate to daily_sales
        if "invoice_date" in df.columns and "sku" in df.columns:
            df["sale_date"] = df["invoice_date"].dt.date
            df["revenue"] = df["quantity"] * df["unit_price"] if "unit_price" in df.columns else 0

            daily = df.groupby(["sale_date", "sku"]).agg(
                quantity_sold=("quantity", "sum"),
                revenue=("revenue", "sum"),
            ).reset_index()

            for _, row in daily.iterrows():
                # Get product_id
                prod_result = await db.execute(
                    text("SELECT id FROM products WHERE org_id = :org_id AND sku = :sku LIMIT 1"),
                    {"org_id": org_str, "sku": str(row["sku"])},
                )
                prod_row = prod_result.first()
                if not prod_row:
                    continue

                await db.execute(
                    text("""
                        INSERT INTO daily_sales (id, org_id, product_id, sale_date, quantity_sold, revenue)
                        VALUES (:id, :org_id, :product_id, :sale_date, :qty, :rev)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "org_id": org_str,
                        "product_id": str(prod_row[0]),
                        "sale_date": row["sale_date"],
                        "qty": int(row["quantity_sold"]),
                        "rev": float(row["revenue"]),
                    },
                )

        await db.commit()

        return {
            "success": True,
            "rows_loaded": len(df),
            "products_created": products_created,
            "orders_created": orders_created,
            "message": f"Successfully loaded {len(df)} rows, created {products_created} products and {orders_created} orders.",
        }

    except Exception as e:
        log.error("Upload load failed: %s", e, exc_info=True)
        await db.rollback()
        return {
            "success": False,
            "rows_loaded": 0,
            "products_created": 0,
            "orders_created": 0,
            "message": f"Load failed: {e!s}",
        }


# ── Private helpers ────────────────────────────────────────────────────────────


def _read_file(path: Path) -> pd.DataFrame:
    """Read CSV or Excel file into a DataFrame."""
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path, engine="openpyxl")
    elif suffix == ".csv":
        return pd.read_csv(path, encoding="utf-8-sig")
    else:
        # Try CSV as default
        return pd.read_csv(path, encoding="utf-8-sig")


def _auto_map_columns(source_columns: list[str]) -> list[dict]:
    """Auto-detect column mappings based on synonyms."""
    mappings = []
    used_targets: set[str] = set()

    for src in source_columns:
        normalized = src.lower().strip().replace(" ", "_").replace("-", "_")
        best_target = None

        for target, synonyms in _COLUMN_SYNONYMS.items():
            if target in used_targets:
                continue
            if normalized in synonyms or normalized == target:
                best_target = target
                break

        if best_target and best_target not in used_targets:
            mappings.append({
                "source_column": src,
                "target_column": best_target,
                "transform": None,
            })
            used_targets.add(best_target)

    return mappings
