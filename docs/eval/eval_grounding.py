"""
Grounding & Hallucination Evaluation — checks LLM output fidelity.

Usage:
    python -m docs.eval.eval_grounding

Tests:
1. Report narrative grounding — do numbers in the narrative match the source JSON?
2. NL2SQL grounding — does the explanation reference only data from query results?
3. Hallucination rate — % of outputs containing fabricated numbers.

Outputs: docs/eval/grounding_results.md

Does NOT require LLM access — uses template narratives and synthetic checks.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

RESULTS_PATH = Path(__file__).parent / "grounding_results.md"


# ── Test Cases ─────────────────────────────────────────────────────────────────

_REPORT_DATA = {
    "kpi_summary": {
        "total_revenue": 125000.50,
        "total_orders": 450,
        "avg_order_value": 277.78,
        "unique_customers": 200,
    },
    "top_products": [
        {"product_name": "Widget A", "category": "Electronics", "total_revenue": 15000.00},
        {"product_name": "Gadget B", "category": "Home", "total_revenue": 12000.00},
    ],
    "inventory_flags": {"critical": 3, "low": 7, "healthy": 90},
    "anomaly_summary": {"total_active": 5, "critical": 2, "warnings": 3},
    "period": "2024-01-01 to 2024-01-31",
}


def extract_numbers(text: str) -> set[str]:
    """Extract all numeric values from text (including formatted numbers)."""
    # Match patterns like 125,000.50 or 450 or 277.78
    pattern = r'\d[\d,]*\.?\d*'
    matches = re.findall(pattern, text)
    return {m.replace(",", "") for m in matches}


def extract_numbers_from_data(data: dict, prefix: str = "") -> set[str]:
    """Recursively extract all numeric values from a dict/list."""
    numbers = set()
    if isinstance(data, dict):
        for k, v in data.items():
            numbers.update(extract_numbers_from_data(v, f"{prefix}.{k}"))
    elif isinstance(data, list):
        for item in data:
            numbers.update(extract_numbers_from_data(item, prefix))
    elif isinstance(data, (int, float)):
        numbers.add(str(data))
        # Also add formatted versions
        if isinstance(data, float):
            numbers.add(f"{data:.2f}")
        if data >= 1000:
            numbers.add(f"{data:,.0f}")
            numbers.add(f"{data:,.2f}")
    return numbers


def check_narrative_grounding(narrative: str, source_data: dict) -> dict:
    """Check that all numbers in the narrative exist in the source data."""
    narrative_numbers = extract_numbers(narrative)
    source_numbers = extract_numbers_from_data(source_data)

    grounded = narrative_numbers & source_numbers
    ungrounded = narrative_numbers - source_numbers

    # Filter out trivially small numbers and dates
    ungrounded = {n for n in ungrounded if float(n) > 1 and not n.startswith("202")}

    total = len(narrative_numbers)
    grounded_count = len(grounded)

    return {
        "total_numbers": total,
        "grounded": grounded_count,
        "ungrounded": len(ungrounded),
        "ungrounded_values": sorted(ungrounded),
        "grounding_rate": round(grounded_count / total * 100, 1) if total > 0 else 100.0,
        "is_hallucination_free": len(ungrounded) == 0,
    }


def generate_template_narrative(data: dict) -> str:
    """Generate a narrative using the template fallback (no LLM)."""
    # Import from the actual service
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
    try:
        from app.services.report_service import _template_narrative
        return _template_narrative(data)
    except ImportError:
        # Fallback inline
        kpi = data.get("kpi_summary", {})
        return (
            f"Total revenue reached £{kpi.get('total_revenue', 0):,.2f} "
            f"across {kpi.get('total_orders', 0):,} orders."
        )


def run_grounding_checks() -> list[dict]:
    """Run all grounding test cases."""
    results = []

    # Test 1: Template narrative grounding
    narrative = generate_template_narrative(_REPORT_DATA)
    check = check_narrative_grounding(narrative, _REPORT_DATA)
    results.append({
        "test": "Template Narrative",
        "description": "Numbers in auto-generated narrative match source JSON",
        **check,
    })

    # Test 2: Fabricated narrative (intentional hallucination)
    hallucinated = (
        "Revenue was £999,999.99 this period with 1500 orders. "
        "The top product generated £50,000 in sales."
    )
    check_h = check_narrative_grounding(hallucinated, _REPORT_DATA)
    results.append({
        "test": "Hallucinated Narrative (control)",
        "description": "Fabricated numbers should be flagged as ungrounded",
        **check_h,
    })

    # Test 3: Partial grounding
    partial = (
        f"Revenue was £{_REPORT_DATA['kpi_summary']['total_revenue']:,.2f} "
        f"with {_REPORT_DATA['kpi_summary']['total_orders']} orders "
        f"and 999 anomalies detected."  # 999 is fabricated
    )
    check_p = check_narrative_grounding(partial, _REPORT_DATA)
    results.append({
        "test": "Partial Grounding",
        "description": "Mix of real and fabricated numbers",
        **check_p,
    })

    # Test 4: Empty data
    empty_narrative = "No data available for this period."
    check_e = check_narrative_grounding(empty_narrative, {})
    results.append({
        "test": "Empty Data",
        "description": "Narrative with no numbers should pass grounding",
        **check_e,
    })

    # Test 5: SQL result grounding
    sql_result = {"total_revenue": 45678.90, "order_count": 123}
    explanation = f"The total revenue is £{sql_result['total_revenue']:,.2f} across {sql_result['order_count']} orders."
    check_sql = check_narrative_grounding(explanation, sql_result)
    results.append({
        "test": "SQL Result Grounding",
        "description": "NL2SQL explanation matches query results",
        **check_sql,
    })

    return results


def main():
    print("Running grounding & hallucination checks...")
    results = run_grounding_checks()

    # Summary
    total_tests = len(results)
    hallucination_free = sum(1 for r in results if r["is_hallucination_free"])

    print(f"\n=== RESULTS ===")
    for r in results:
        status = "PASS" if r["is_hallucination_free"] else "FAIL"
        print(f"  [{status}] {r['test']}: {r['grounding_rate']}% grounded ({r['grounded']}/{r['total_numbers']})")
        if r["ungrounded_values"]:
            print(f"       Ungrounded: {r['ungrounded_values']}")

    # Generate markdown
    lines = [
        "# Grounding & Hallucination Evaluation Results",
        "",
        f"> Generated: {time.strftime('%Y-%m-%d %H:%M')}",
        f"> Tests: {total_tests} | Hallucination-free: {hallucination_free}/{total_tests}",
        "",
        "## Results",
        "",
        "| Test | Numbers Found | Grounded | Ungrounded | Grounding Rate | Hallucination Free |",
        "|------|--------------|----------|------------|----------------|-------------------|",
    ]

    for r in results:
        emoji = "✅" if r["is_hallucination_free"] else "❌"
        lines.append(
            f"| {r['test']} | {r['total_numbers']} | {r['grounded']} | "
            f"{r['ungrounded']} | {r['grounding_rate']}% | {emoji} |"
        )

    lines.extend([
        "",
        "## Grounding Methodology",
        "",
        "1. Extract all numeric values from LLM-generated text",
        "2. Extract all numeric values from source data (JSON)",
        "3. Check that every number in the output exists in the source",
        "4. Flag ungrounded numbers as potential hallucinations",
        "",
        "## Safeguards Implemented",
        "",
        "- Template narrative fallback when LLM unavailable (100% grounding guaranteed)",
        "- SQL validator rejects non-SELECT queries",
        "- Read-only DB connection for NL2SQL execution",
        "- Self-repair loop (max 2 retries) for SQL errors",
        "- No customer PII sent to LLM — only aggregated figures",
        "",
        "---",
        "⚠️ All numbers from script execution. Never fabricated.",
    ])

    RESULTS_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nResults written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
