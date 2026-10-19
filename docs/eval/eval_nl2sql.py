"""
NL2SQL Evaluation Script — runs the gold set and produces an ablation table.

Usage:
    python -m docs.eval.eval_nl2sql

Reads: docs/eval/nl2sql_gold.jsonl
Outputs: docs/eval/nl2sql_results.md

Evaluates:
- SQL validity (is it valid SELECT)
- SQL correctness (contains expected fragments)
- Answer relevance (contains expected keywords)
- Ablation: baseline → +glossary → +schema linking → +self-repair
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

# Add the backend to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

GOLD_PATH = Path(__file__).parent / "nl2sql_gold.jsonl"
RESULTS_PATH = Path(__file__).parent / "nl2sql_results.md"

# Dangerous SQL patterns (should never appear)
_DANGEROUS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


def load_gold_set() -> list[dict]:
    """Load the gold set from JSONL."""
    items = []
    with open(GOLD_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def evaluate_sql_validity(sql: str | None) -> dict:
    """Check if generated SQL is a valid, safe SELECT."""
    if not sql:
        return {"valid": False, "safe": True, "reason": "No SQL generated"}

    is_select = bool(re.match(r"^\s*SELECT\b", sql, re.IGNORECASE))
    is_safe = not bool(_DANGEROUS.search(sql))

    return {
        "valid": is_select,
        "safe": is_safe,
        "reason": None if (is_select and is_safe) else "Non-SELECT or dangerous SQL",
    }


def evaluate_sql_correctness(sql: str | None, expected_contains: list[str]) -> dict:
    """Check if SQL contains expected fragments."""
    if not sql:
        return {"score": 0.0, "matched": 0, "total": len(expected_contains)}

    sql_upper = sql.upper()
    matched = sum(1 for frag in expected_contains if frag.upper() in sql_upper)

    return {
        "score": matched / len(expected_contains) if expected_contains else 1.0,
        "matched": matched,
        "total": len(expected_contains),
    }


def evaluate_answer_relevance(answer: str | None, expected_contains: list[str]) -> dict:
    """Check if the answer contains expected keywords."""
    if not answer:
        return {"score": 0.0, "matched": 0, "total": len(expected_contains)}

    answer_lower = answer.lower()
    matched = sum(1 for kw in expected_contains if kw.lower() in answer_lower)

    return {
        "score": matched / len(expected_contains) if expected_contains else 1.0,
        "matched": matched,
        "total": len(expected_contains),
    }


def run_offline_evaluation() -> dict:
    """
    Run offline evaluation (no LLM calls) using the gold set structure.
    This validates the gold set itself and produces category-level stats.
    """
    gold = load_gold_set()

    # Category breakdown
    categories: dict[str, dict] = {}
    for item in gold:
        cat = item.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"count": 0, "avg_fragments": 0}
        categories[cat]["count"] += 1
        categories[cat]["avg_fragments"] += len(item.get("expected_sql_contains", []))

    for cat_data in categories.values():
        if cat_data["count"] > 0:
            cat_data["avg_fragments"] = round(cat_data["avg_fragments"] / cat_data["count"], 1)

    return {
        "total_questions": len(gold),
        "categories": categories,
        "gold_set_valid": len(gold) >= 50,
    }


def generate_results_markdown() -> str:
    """Generate the evaluation results as a Markdown document."""
    stats = run_offline_evaluation()
    gold = load_gold_set()

    lines = [
        "# NL2SQL Evaluation Results",
        "",
        f"> Generated: {time.strftime('%Y-%m-%d %H:%M')}",
        f"> Gold set size: **{stats['total_questions']}** questions",
        "",
        "## Gold Set Coverage",
        "",
        "| Category | Questions | Avg SQL Fragments |",
        "|----------|-----------|-------------------|",
    ]

    for cat, data in sorted(stats["categories"].items()):
        lines.append(f"| {cat} | {data['count']} | {data['avg_fragments']} |")

    lines.extend([
        "",
        "## Ablation Table (Template)",
        "",
        "| Configuration | SQL Validity | SQL Correctness | Answer Relevance | Avg Latency (ms) |",
        "|---------------|-------------|-----------------|------------------|-------------------|",
        "| Baseline (no context) | — | — | — | — |",
        "| + Metric Dictionary | — | — | — | — |",
        "| + Schema Linking / RAG | — | — | — | — |",
        "| + Self-Repair (2 retries) | — | — | — | — |",
        "| **Full Pipeline** | — | — | — | — |",
        "",
        "> ⚠️ Fill in actual numbers by running `python -m docs.eval.eval_nl2sql --live`",
        "> against a running instance with seeded data and LLM access.",
        "",
        "## Metrics Definitions",
        "",
        "- **SQL Validity**: % of generated SQL that is a valid SELECT (no dangerous keywords)",
        "- **SQL Correctness**: avg fraction of expected SQL fragments present in generated SQL",
        "- **Answer Relevance**: avg fraction of expected keywords present in the narrative answer",
        "- **Avg Latency**: p50 end-to-end time per question (ms)",
        "",
        "## Safety Checks",
        "",
        "- [ ] No INSERT/UPDATE/DELETE/DROP generated across all 50 questions",
        "- [ ] All queries contain org_id filter",
        "- [ ] No customer PII in LLM prompts",
        "",
        "## Category Breakdown",
        "",
    ])

    for cat, data in sorted(stats["categories"].items()):
        lines.append(f"### {cat.title()} ({data['count']} questions)")
        lines.append("")
        cat_items = [g for g in gold if g.get("category") == cat]
        for item in cat_items[:3]:
            lines.append(f"- Q{item['id']}: *{item['question']}*")
        if len(cat_items) > 3:
            lines.append(f"- ... and {len(cat_items) - 3} more")
        lines.append("")

    lines.extend([
        "---",
        "⚠️ All metrics must come from actual script runs. Never fabricate numbers.",
    ])

    return "\n".join(lines)


def main():
    """Generate the evaluation results document."""
    print(f"Loading gold set from {GOLD_PATH}...")
    stats = run_offline_evaluation()
    print(f"  Total questions: {stats['total_questions']}")
    print(f"  Categories: {list(stats['categories'].keys())}")
    print(f"  Gold set valid: {stats['gold_set_valid']}")

    results_md = generate_results_markdown()
    RESULTS_PATH.write_text(results_md, encoding="utf-8")
    print(f"\nResults written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
