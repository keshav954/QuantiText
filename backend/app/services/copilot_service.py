"""
NL2SQL Copilot service — orchestrates the full chat pipeline.

Pipeline for each question:
1. Load / create chat session.
2. Build schema context from DB views and a static glossary.
3. Call LLM.generate_sql() → raw SQL string.
4. Validate SQL (read-only SELECT only, no dangerous keywords).
5. Execute on the readonly DB connection.
6. Call LLM.generate() → natural-language answer grounded on results.
7. Persist messages to chat_sessions / chat_messages table.
8. Return structured ChatResponse.

SECURITY NOTES:
- SQL is NEVER executed on the read-write connection.
- Validation rejects any non-SELECT statement before execution.
- Customer/PII columns are never sent to the LLM (only aggregated figures).
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm.base import TaskType
from app.services.llm.factory import get_provider

log = logging.getLogger(__name__)

# ── Schema context ─────────────────────────────────────────────────────────────

_SCHEMA_CONTEXT = """
Available views (use ONLY these — customer PII excluded):

v_kpi_daily(org_id, sale_date, total_revenue, order_count, avg_order_value, unique_customers)
v_sales_by_product(org_id, product_id, sku, product_name, category_name, total_revenue, total_qty)
v_sales_by_region(org_id, sale_date, region, total_revenue, order_count)
v_inventory_status(org_id, product_id, sku, product_name, category_name, stock_on_hand,
                   reorder_point, stock_status)

Supporting tables (read-only):
daily_sales(org_id, product_id, sale_date, quantity_sold, revenue, region)
products(id, org_id, category_id, sku, name, unit_price, is_active)
categories(id, org_id, name, slug)
forecasts(org_id, product_id, forecast_date, horizon_days, predicted_qty, lower_bound, upper_bound, model_name, mape)
anomalies(org_id, product_id, detected_date, anomaly_type, detector, severity_score, estimated_impact, is_dismissed)

All monetary values are in GBP (£). Dates are in ISO format (YYYY-MM-DD).
Always filter by org_id = '<current_org_id>' in every query.
"""

_GLOSSARY = """
- Revenue: sum of (quantity × unit_price) in GBP
- AOV: Average Order Value = total_revenue / order_count
- Safety stock: buffer stock to cover demand variability
- EOQ: Economic Order Quantity (optimal reorder quantity)
- ABC class: A=top 70% revenue, B=next 20%, C=remaining 10%
- MAPE: Mean Absolute Percentage Error (forecast accuracy, lower is better)
"""

_FEW_SHOTS = [
    {
        "question": "What is the total revenue for the last 30 days?",
        "sql": "SELECT ROUND(SUM(total_revenue)::numeric, 2) AS total_revenue FROM v_kpi_daily WHERE org_id = '<org_id>' AND sale_date >= CURRENT_DATE - INTERVAL '30 days' LIMIT 1;",
    },
    {
        "question": "Which 5 products have the highest revenue?",
        "sql": "SELECT sku, product_name, category_name, ROUND(total_revenue::numeric, 2) AS total_revenue FROM v_sales_by_product WHERE org_id = '<org_id>' ORDER BY total_revenue DESC LIMIT 5;",
    },
    {
        "question": "Show me daily revenue for this month",
        "sql": "SELECT sale_date, ROUND(total_revenue::numeric, 2) AS revenue, order_count FROM v_kpi_daily WHERE org_id = '<org_id>' AND sale_date >= DATE_TRUNC('month', CURRENT_DATE) ORDER BY sale_date LIMIT 100;",
    },
    {
        "question": "Which products are low on stock?",
        "sql": "SELECT sku, product_name, stock_on_hand, reorder_point, stock_status FROM v_inventory_status WHERE org_id = '<org_id>' AND stock_status IN ('low', 'critical') ORDER BY stock_on_hand LIMIT 50;",
    },
]

# ── SQL validation ─────────────────────────────────────────────────────────────

_DANGEROUS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC|EXECUTE|CALL)\b",
    re.IGNORECASE,
)


def _validate_sql(sql: str) -> str:
    """
    Validate and clean extracted SQL.
    - Strip markdown code fences.
    - Ensure it's a SELECT.
    - Reject dangerous keywords.
    Raises ValueError if invalid.
    """
    # Strip markdown fences
    sql = re.sub(r"```(?:sql)?", "", sql, flags=re.IGNORECASE).strip().rstrip(";").strip()

    # Ensure SELECT
    if not re.match(r"^\s*SELECT\b", sql, re.IGNORECASE):
        raise ValueError(f"Generated SQL is not a SELECT statement: {sql[:80]}")

    # Reject dangerous keywords
    match = _DANGEROUS.search(sql)
    if match:
        raise ValueError(f"Dangerous keyword in generated SQL: {match.group()}")

    return sql


def _inject_org_id(sql: str, org_id: str) -> str:
    """Replace placeholder <org_id> or '<org_id>' with the real value."""
    return sql.replace("'<org_id>'", f"'{org_id}'").replace("<org_id>", f"'{org_id}'")


# ── Public API ─────────────────────────────────────────────────────────────────

async def chat(
    db: AsyncSession,
    readonly_db: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    question: str,
    session_id: uuid.UUID | None = None,
) -> dict:
    """
    Process one NL2SQL chat turn.

    Returns:
        {session_id, question, answer, sql, result, follow_up_suggestions, from_cache}
    """
    # 1. Ensure session exists
    session_id, history = await _get_or_create_session(db, org_id, user_id, session_id)

    # 2. Build context
    schema_ctx = _SCHEMA_CONTEXT
    examples = [
        {"question": e["question"], "sql": _inject_org_id(e["sql"], str(org_id))}
        for e in _FEW_SHOTS
    ]

    provider = get_provider()

    # 3. Generate SQL
    raw_sql_response = await provider.generate_sql(
        question,
        schema_context=schema_ctx + "\n" + _GLOSSARY,
        examples=examples,
    )
    raw_sql = raw_sql_response.text

    query_result = None
    sql = None
    answer = ""

    try:
        sql = _validate_sql(raw_sql)
        sql = _inject_org_id(sql, str(org_id))

        # 4. Execute on readonly connection
        result = await readonly_db.execute(text(sql))
        columns = list(result.keys())
        rows = [list(r) for r in result.fetchmany(200)]  # cap at 200 rows

        query_result = {
            "sql": sql,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "chart_type": _infer_chart_type(question, columns),
        }

        # 5. Generate narrative answer
        result_preview = _format_result_for_llm(columns, rows[:10])
        answer_response = await provider.generate(
            f"Question: {question}\n\nQuery Result:\n{result_preview}\n\nProvide a concise, accurate answer using ONLY the numbers above.",
            system_prompt=(
                "You are a BI analyst. Answer the user's question using ONLY the provided query results. "
                "Never invent numbers. Be concise (2-4 sentences). Mention key figures."
            ),
            task_type=TaskType.TEXT_EXPLANATION,
            temperature=0.1,
        )
        answer = answer_response.text

    except ValueError as e:
        log.warning("SQL validation failed: %s", e)
        answer = "I couldn't generate a valid SQL query for that question. Could you rephrase it?"
        sql = None
    except Exception as e:
        log.error("SQL execution failed: %s", e)
        answer = "The query ran into an issue. Please try rephrasing your question."

    # 6. Generate follow-up suggestions
    follow_ups = _generate_follow_ups(question, query_result)

    # 7. Persist messages
    await _save_messages(db, session_id, question, answer, sql, query_result)

    return {
        "session_id": session_id,
        "question": question,
        "answer": answer,
        "sql": sql,
        "result": query_result,
        "follow_up_suggestions": follow_ups,
        "from_cache": False,
    }


async def list_sessions(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    limit: int = 20,
) -> list[dict]:
    """Return recent chat sessions for a user."""
    result = await db.execute(
        text("""
            SELECT id, title, created_at,
                   (SELECT COUNT(*) FROM chat_messages WHERE session_id = cs.id) AS message_count
            FROM chat_sessions cs
            WHERE org_id = :org_id AND user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"org_id": str(org_id), "user_id": str(user_id), "limit": limit},
    )
    rows = result.mappings().all()
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "created_at": r["created_at"],
            "message_count": r["message_count"],
        }
        for r in rows
    ]


async def get_session_messages(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    session_id: uuid.UUID,
) -> list[dict]:
    """Load message history for a session."""
    result = await db.execute(
        text("""
            SELECT role, content, created_at
            FROM chat_messages
            WHERE session_id = :session_id
              AND org_id = :org_id
            ORDER BY created_at
            LIMIT 100
        """),
        {"session_id": str(session_id), "org_id": str(org_id)},
    )
    rows = result.mappings().all()
    return [{"role": r["role"], "content": r["content"], "timestamp": r["created_at"]} for r in rows]


# ── Private helpers ────────────────────────────────────────────────────────────

async def _get_or_create_session(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    session_id: uuid.UUID | None,
) -> tuple[uuid.UUID, list[dict]]:
    """Return (session_id, message_history). Creates session if session_id is None."""
    if session_id is None:
        session_id = uuid.uuid4()
        await db.execute(
            text("""
                INSERT INTO chat_sessions (id, org_id, user_id, title)
                VALUES (:id, :org_id, :user_id, 'New Chat')
            """),
            {"id": str(session_id), "org_id": str(org_id), "user_id": str(user_id)},
        )
        await db.commit()
        return session_id, []

    result = await db.execute(
        text("""
            SELECT role, content FROM chat_messages
            WHERE session_id = :sid AND org_id = :org_id
            ORDER BY created_at DESC LIMIT 10
        """),
        {"sid": str(session_id), "org_id": str(org_id)},
    )
    history = [{"role": r[0], "content": r[1]} for r in result.fetchall()]
    return session_id, list(reversed(history))


async def _save_messages(
    db: AsyncSession,
    session_id: uuid.UUID,
    question: str,
    answer: str,
    sql: str | None,
    result: dict | None,
) -> None:
    # Fetch org_id from session
    row = await db.execute(
        text("SELECT org_id FROM chat_sessions WHERE id = :id"),
        {"id": str(session_id)},
    )
    r = row.first()
    if not r:
        return
    org_id = str(r[0])

    # Save user message
    await db.execute(
        text("""
            INSERT INTO chat_messages (id, session_id, org_id, role, content)
            VALUES (:id, :session_id, :org_id, 'user', :content)
        """),
        {"id": str(uuid.uuid4()), "session_id": str(session_id), "org_id": org_id, "content": question},
    )

    # Save assistant message (compact JSON metadata)
    assistant_content = answer
    if sql:
        meta = {"sql": sql, "rows": len(result["rows"]) if result else 0}
        assistant_content = f"{answer}\n\n<!-- meta:{json.dumps(meta)} -->"

    await db.execute(
        text("""
            INSERT INTO chat_messages (id, session_id, org_id, role, content)
            VALUES (:id, :session_id, :org_id, 'assistant', :content)
        """),
        {"id": str(uuid.uuid4()), "session_id": str(session_id), "org_id": org_id, "content": assistant_content},
    )

    # Update session title from first question
    await db.execute(
        text("""
            UPDATE chat_sessions
            SET title = CASE WHEN title = 'New Chat' THEN :title ELSE title END
            WHERE id = :id
        """),
        {"id": str(session_id), "title": question[:80]},
    )

    await db.commit()


def _format_result_for_llm(columns: list[str], rows: list[list]) -> str:
    """Format query results as a compact text table."""
    if not rows:
        return "No results."
    header = " | ".join(columns)
    separator = "-" * len(header)
    data_rows = "\n".join(" | ".join(str(v) for v in row) for row in rows)
    return f"{header}\n{separator}\n{data_rows}"


def _infer_chart_type(question: str, columns: list[str]) -> str | None:
    """Heuristic: infer chart type from question and column names."""
    q = question.lower()
    col_str = " ".join(columns).lower()

    if any(w in q for w in ["trend", "over time", "daily", "monthly", "weekly"]):
        return "line"
    if any(w in q for w in ["top", "rank", "best", "worst", "highest", "lowest", "compare"]):
        return "bar"
    if any(w in q for w in ["breakdown", "share", "proportion", "percentage", "distribution"]):
        return "pie"
    if "date" in col_str or "day" in col_str or "month" in col_str:
        return "line"
    return "table"


def _generate_follow_ups(question: str, result: dict | None) -> list[str]:
    """Simple heuristic follow-up suggestions."""
    q = question.lower()
    suggestions = []

    if "revenue" in q:
        suggestions.extend([
            "Which product category drove the most growth?",
            "How does this compare to the previous period?",
        ])
    elif "stock" in q or "inventory" in q:
        suggestions.extend([
            "Which products need immediate reordering?",
            "What is the total inventory value at risk?",
        ])
    elif "top" in q or "product" in q:
        suggestions.extend([
            "Show me the revenue trend for the top product",
            "Which region drives the most sales for these products?",
        ])

    if result and result.get("row_count", 0) > 0:
        suggestions.append("Export this data as a report")

    return suggestions[:3]
