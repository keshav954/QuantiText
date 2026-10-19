"""
Anomaly Detection Evaluation — precision, recall, F1 per detector.

Usage:
    python -m docs.eval.eval_anomaly

Injects synthetic anomalies into a clean dataset and measures
how well each detector (zscore, iforest, data_quality) recovers them.

Outputs: docs/eval/anomaly_results.md
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

RESULTS_PATH = Path(__file__).parent / "anomaly_results.md"

# Thresholds (must match anomaly_service.py)
_ZSCORE_THRESHOLD = 2.5
_MIN_HISTORY_DAYS = 14


def generate_clean_data(n_products: int = 10, n_days: int = 90) -> pd.DataFrame:
    """Generate clean synthetic daily sales data."""
    rng = np.random.default_rng(42)
    rows = []
    for p in range(n_products):
        base_rev = rng.uniform(50, 500)
        base_qty = rng.integers(5, 50)
        for d in range(n_days):
            noise = rng.normal(0, base_rev * 0.1)
            rows.append({
                "product_id": f"product_{p}",
                "sale_date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=d),
                "revenue": max(0, base_rev + noise),
                "quantity_sold": max(0, int(base_qty + rng.normal(0, 3))),
            })
    return pd.DataFrame(rows)


def inject_anomalies(df: pd.DataFrame, n_spikes: int = 15, n_drops: int = 10, n_zeros: int = 5) -> tuple[pd.DataFrame, set]:
    """Inject known anomalies. Returns (modified_df, set of (product_id, date) ground truth)."""
    rng = np.random.default_rng(123)
    df = df.copy()
    ground_truth: set[tuple[str, str]] = set()

    # Revenue spikes (5x normal)
    eligible = df[df["revenue"] > 0].index.tolist()
    spike_indices = rng.choice(eligible, size=min(n_spikes, len(eligible)), replace=False)
    for idx in spike_indices:
        df.loc[idx, "revenue"] *= 5.0
        gt_key = (df.loc[idx, "product_id"], str(df.loc[idx, "sale_date"].date()))
        ground_truth.add(gt_key)

    # Revenue drops (near zero)
    drop_indices = rng.choice(eligible, size=min(n_drops, len(eligible)), replace=False)
    for idx in drop_indices:
        df.loc[idx, "revenue"] = 0.01
        gt_key = (df.loc[idx, "product_id"], str(df.loc[idx, "sale_date"].date()))
        ground_truth.add(gt_key)

    # Zero-sales stretches (5 consecutive days)
    products = df["product_id"].unique()
    for _ in range(n_zeros):
        prod = rng.choice(products)
        prod_mask = df["product_id"] == prod
        prod_idx = df[prod_mask].index
        if len(prod_idx) < 20:
            continue
        start = rng.choice(prod_idx[5:-5])
        for offset in range(5):
            if start + offset in df.index:
                df.loc[start + offset, "quantity_sold"] = 0
                df.loc[start + offset, "revenue"] = 0
                gt_key = (df.loc[start + offset, "product_id"], str(df.loc[start + offset, "sale_date"].date()))
                ground_truth.add(gt_key)

    return df, ground_truth


def detect_zscore(df: pd.DataFrame) -> set[tuple[str, str]]:
    """Run z-score detector (mirrors anomaly_service.py)."""
    detected: set[tuple[str, str]] = set()
    for product_id, grp in df.groupby("product_id"):
        if len(grp) < _MIN_HISTORY_DAYS:
            continue
        grp = grp.sort_values("sale_date")
        rev = grp["revenue"].astype(float)
        mu, sigma = rev.mean(), rev.std()
        if sigma < 1e-6:
            continue
        z = (rev - mu) / sigma
        for i, (_, row) in enumerate(grp.iterrows()):
            if abs(float(z.iloc[i])) > _ZSCORE_THRESHOLD:
                detected.add((str(product_id), str(row["sale_date"].date())))
    return detected


def detect_iforest(df: pd.DataFrame) -> set[tuple[str, str]]:
    """Run Isolation Forest detector (mirrors anomaly_service.py)."""
    from sklearn.ensemble import IsolationForest

    detected: set[tuple[str, str]] = set()
    for product_id, grp in df.groupby("product_id"):
        if len(grp) < _MIN_HISTORY_DAYS:
            continue
        X = grp[["revenue", "quantity_sold"]].astype(float).values
        clf = IsolationForest(contamination=0.05, random_state=42)
        preds = clf.fit_predict(X)
        for i, (_, row) in enumerate(grp.iterrows()):
            if preds[i] == -1:
                detected.add((str(product_id), str(row["sale_date"].date())))
    return detected


def detect_data_quality(df: pd.DataFrame) -> set[tuple[str, str]]:
    """Detect consecutive zero-sales streaks (mirrors anomaly_service.py)."""
    detected: set[tuple[str, str]] = set()
    for product_id, grp in df.groupby("product_id"):
        grp = grp.sort_values("sale_date")
        consecutive = 0
        for _, row in grp.iterrows():
            if row["quantity_sold"] == 0:
                consecutive += 1
                if consecutive >= 3:
                    detected.add((str(product_id), str(row["sale_date"].date())))
            else:
                consecutive = 0
    return detected


def compute_metrics(ground_truth: set, detected: set) -> dict:
    """Compute precision, recall, F1."""
    tp = len(ground_truth & detected)
    fp = len(detected - ground_truth)
    fn = len(ground_truth - detected)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }


def main():
    print("Generating clean synthetic data...")
    clean_df = generate_clean_data()

    print("Injecting synthetic anomalies...")
    dirty_df, ground_truth = inject_anomalies(clean_df)
    print(f"  Ground truth anomalies: {len(ground_truth)}")

    results = {}

    print("Running Z-score detector...")
    zscore_detected = detect_zscore(dirty_df)
    results["zscore"] = compute_metrics(ground_truth, zscore_detected)
    print(f"  Detected: {len(zscore_detected)}, P={results['zscore']['precision']}, R={results['zscore']['recall']}, F1={results['zscore']['f1']}")

    print("Running Isolation Forest detector...")
    iforest_detected = detect_iforest(dirty_df)
    results["iforest"] = compute_metrics(ground_truth, iforest_detected)
    print(f"  Detected: {len(iforest_detected)}, P={results['iforest']['precision']}, R={results['iforest']['recall']}, F1={results['iforest']['f1']}")

    print("Running Data Quality detector...")
    dq_detected = detect_data_quality(dirty_df)
    results["data_quality"] = compute_metrics(ground_truth, dq_detected)
    print(f"  Detected: {len(dq_detected)}, P={results['data_quality']['precision']}, R={results['data_quality']['recall']}, F1={results['data_quality']['f1']}")

    # Combined
    all_detected = zscore_detected | iforest_detected | dq_detected
    results["combined"] = compute_metrics(ground_truth, all_detected)
    print(f"\nCombined: Detected: {len(all_detected)}, P={results['combined']['precision']}, R={results['combined']['recall']}, F1={results['combined']['f1']}")

    # Generate markdown
    lines = [
        "# Anomaly Detection Evaluation Results",
        "",
        f"> Generated: {time.strftime('%Y-%m-%d %H:%M')}",
        f"> Synthetic dataset: 10 products × 90 days",
        f"> Ground truth anomalies: {len(ground_truth)}",
        "",
        "## Precision / Recall / F1 per Detector",
        "",
        "| Detector | TP | FP | FN | Precision | Recall | F1 |",
        "|----------|----|----|----|-----------|---------|----|",
    ]

    for name, m in results.items():
        lines.append(
            f"| {name} | {m['tp']} | {m['fp']} | {m['fn']} | "
            f"{m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} |"
        )

    lines.extend([
        "",
        "## Notes",
        "",
        "- Data is **SYNTHETIC** — generated for evaluation only.",
        "- Injected anomalies: 15 revenue spikes (5×), 10 revenue drops, 5 zero-sales streaks.",
        "- Isolation Forest uses contamination=0.05, random_state=42.",
        "- Z-score threshold: 2.5 (matches production config).",
        "- Data Quality flags 3+ consecutive zero-sales days.",
        "",
        "---",
        "⚠️ All numbers in this file are from script execution. Never fabricated.",
    ])

    RESULTS_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nResults written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
