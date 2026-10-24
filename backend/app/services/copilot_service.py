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

import sqlglot
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlglot import exp

from app.services.llm.base import TaskType
from app.services.llm.factory import get_provider

log = logging.getLogger(__name__)

# ── Schema context ─────────────────────────────────────────────────────────────

_SCHEMA_CONTEXT = """
Available views (use ONLY these — customer PII excluded):

v_kpi_daily(org_id, sale_date, total_revenue, order_count, avg_order_value, unique_customers)
v_sales_by_product(org_id, product_id, sku, product_name, category_name, total_revenue, total_qty)
v_sales_by_region(org_id, sale_date, region, total_revenue, total_qty)
v_inventory_status(org_id, product_id, sku, product_name, category_name, stock_on_hand,
                   reorder_point, lead_time_days, status_label)

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
        "sql": "SELECT sku, product_name, stock_on_hand, reorder_point, status_label FROM v_inventory_status WHERE org_id = '<org_id>' AND status_label IN ('low_stock', 'out_of_stock') ORDER BY stock_on_hand LIMIT 50;",
    },
]

# ── SQL validation (sqlglot AST verification) ─────────────────────────────────

ALLOWED_VIEWS: set[str] = {
    "v_kpi_daily",
    "v_sales_by_product",
    "v_sales_by_region",
    "v_inventory_status",
}

# Allow both aggregated views and read-only schema tables
ALLOWED_TABLES: set[str] = {
    "v_kpi_daily",
    "v_sales_by_product",
    "v_sales_by_region",
    "v_inventory_status",
    "daily_sales",
    "products",
    "categories",
    "forecasts",
    "anomalies",
}

BLOCKED_FUNCTIONS: set[str] = {
    "pg_sleep",
    "pg_read_file",
    "pg_write_file",
    "pg_read_binary_file",
    "query_to_xml",
    "dblink",
    "eval",
    "current_setting",
    "set_config",
    "version",
}


_DANGEROUS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC|EXECUTE|CALL)\b",
    re.IGNORECASE,
)


def _extract_sql_from_text(raw: str) -> str:
    """Extract clean SQL string from LLM output (fenced code block or raw query)."""
    cleaned = raw.strip()

    # Look for markdown code fence first
    match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    else:
        # If no code fence, find start of SELECT or WITH
        select_match = re.search(r"\b(SELECT|WITH)\b[\s\S]*", cleaned, re.IGNORECASE)
        if select_match:
            cleaned = select_match.group(0).strip()

    return cleaned.rstrip(";").strip()


def _validate_sql(sql: str) -> str:
    """
    Validate and clean extracted SQL (backward compatibility).
    Ensures query parses as a SELECT and does not contain dangerous keywords.
    """
    cleaned = re.sub(r"```(?:sql)?", "", sql, flags=re.IGNORECASE).strip().rstrip(";").strip()

    # Ensure SELECT prefix first
    if not re.match(r"^\s*SELECT\b", cleaned, re.IGNORECASE):
        raise ValueError(f"Generated SQL is not a SELECT statement: {cleaned[:80]}")

    # Reject dangerous keywords
    match = _DANGEROUS.search(cleaned)
    if match:
        raise ValueError(f"Dangerous keyword in generated SQL: {match.group()}")

    try:
        expression = sqlglot.parse_one(cleaned, read="postgres")
    except Exception as e:
        raise ValueError(f"Invalid SQL syntax: {e}") from e

    if not isinstance(expression, exp.Select):
        raise ValueError(f"Generated SQL is not a SELECT statement: {cleaned[:80]}")

    return cleaned


def validate_and_secure_sql(sql: str, org_id: str) -> str:
    """
    Parse and validate generated SQL using sqlglot AST:
    1. Extract SQL from markdown or conversational fences.
    2. Enforce only SELECT statements.
    3. Allowlist tables/views strictly to safe BI views and tables (customer PII excluded).
    4. Block malicious function calls (pg_sleep, filesystem access, etc.).
    5. Enforce tenant isolation by verifying or injecting org_id in the WHERE clause.
    """
    # 1. Clean and extract SQL
    cleaned = _extract_sql_from_text(sql)
    if not cleaned:
        raise ValueError("Generated SQL statement is empty.")

    # Reject dangerous keywords directly
    match = _DANGEROUS.search(cleaned)
    if match:
        raise ValueError(f"Dangerous keyword in generated SQL: {match.group()}")

    # 2. Parse into AST
    try:
        expression = sqlglot.parse_one(cleaned, read="postgres")
    except Exception as e:
        raise ValueError(f"Invalid SQL syntax: {e}") from e

    # 3. Restrict to SELECT only
    if not isinstance(expression, exp.Select):
        raise ValueError("Only read-only SELECT queries are permitted.")

    # 4. Check tables against allowlist (excluding CTE aliases)
    cte_names = {
        cte.alias_or_name.lower() for cte in expression.find_all(exp.CTE) if cte.alias_or_name
    }
    tables = [t.name.lower() for t in expression.find_all(exp.Table) if t.name]

    for table_name in tables:
        if table_name in cte_names:
            continue
        if table_name not in ALLOWED_TABLES:
            raise ValueError(
                f"Querying '{table_name}' is not permitted. "
                f"Allowed views and tables: {', '.join(sorted(ALLOWED_TABLES))}."
            )

    # 5. Block dangerous functions
    for func in expression.find_all((exp.Func, exp.Anonymous)):
        fname = (func.name if hasattr(func, "name") and func.name else func.key or "").lower()
        if fname in BLOCKED_FUNCTIONS:
            raise ValueError(f"Function call '{fname}()' is blocked for security reasons.")

    # 6. Tenant isolation: replace placeholders and ensure org_id filter
    sql_str = expression.sql("postgres")
    sql_str = sql_str.replace("'<org_id>'", f"'{org_id}'").replace("<org_id>", f"'{org_id}'")

    reparsed = sqlglot.parse_one(sql_str, read="postgres")
    has_org_filter = False
    for eq in reparsed.find_all(exp.EQ):
        left_col = eq.left.name if isinstance(eq.left, exp.Column) else ""
        right_col = eq.right.name if isinstance(eq.right, exp.Column) else ""
        if left_col.lower() == "org_id" or right_col.lower() == "org_id":
            has_org_filter = True
            break

    # If the LLM omitted org_id from the WHERE clause, inject it automatically
    if not has_org_filter and tables:
        reparsed = reparsed.where(f"org_id = '{org_id}'")

    return reparsed.sql("postgres")


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

    # Check if the question is a greeting or general help request
    clean_q = question.strip().lower().rstrip("?!.")
    if clean_q in {
        "hi",
        "hello",
        "hey",
        "help",
        "who are you",
        "what can you do",
        "what can you do for me",
        "thanks",
        "thank you",
        "good morning",
        "good afternoon",
        "good evening",
    }:
        answer = (
            "Hello! I am your QuantiText AI Copilot. I can query your business data in real time.\n\n"
            "Here are a few questions you can ask me:\n"
            '• **Revenue & KPIs**: *"What is the total revenue for the last 30 days?"*\n'
            '• **Top Performers**: *"Which 5 products have the highest revenue?"*\n'
            '• **Inventory Health**: *"Which products are low on stock or need reordering?"*\n'
            '• **Trends**: *"Show me daily revenue trends for this month"*\n'
            '• **Regional**: *"What is our sales breakdown by region?"*\n\n'
            "What would you like to analyze?"
        )
        follow_ups = [
            "What is the total revenue for the last 30 days?",
            "Which 5 products have the highest revenue?",
            "Which products are low on stock?",
        ]
        await _save_messages(db, session_id, question, answer, None, None)
        return {
            "session_id": session_id,
            "question": question,
            "answer": answer,
            "sql": None,
            "result": None,
            "follow_up_suggestions": follow_ups,
            "from_cache": False,
        }

    provider = get_provider()

    # 3. Generate SQL with self-repair loop (max 2 retries)
    max_retries = 2
    current_attempt = 0
    raw_sql = None
    query_result = None
    sql = None
    answer = ""
    last_error = ""

    while current_attempt <= max_retries:
        if current_attempt == 0:
            raw_sql_response = await provider.generate_sql(
                question,
                schema_context=schema_ctx + "\n" + _GLOSSARY,
                examples=examples,
            )
        else:
            log.info(
                "NL2SQL Self-repair attempt %d for query error: %s",
                current_attempt,
                last_error,
            )
            repair_prompt = (
                f"User Question: {question}\n\n"
                f"Previous SQL attempt:\n{raw_sql}\n\n"
                f"Database error encountered:\n{last_error}\n\n"
                f"Please fix the SQL query to resolve this error using ONLY the available schema views."
            )
            raw_sql_response = await provider.generate_sql(
                repair_prompt,
                schema_context=schema_ctx + "\n" + _GLOSSARY,
                examples=examples,
            )

        raw_sql = raw_sql_response.text

        try:
            sql = validate_and_secure_sql(raw_sql, str(org_id))

            # 4. Execute on readonly connection
            result = await readonly_db.execute(text(sql))
            columns = list(result.keys())
            rows = [list(r) for r in result.fetchmany(200)]  # cap at 200 rows

            query_result = {
                "sql": sql,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "chart_type": _infer_chart_type(question, columns, len(rows)),
            }

            # 5. Generate narrative answer (only aggregated summary sent to LLM)
            result_preview = _format_result_for_llm(columns, rows, len(rows))
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
            break

        except ValueError as e:
            last_error = f"SQL validation failed: {e}"
            log.warning("SQL validation attempt %d failed: %s", current_attempt, e)
            current_attempt += 1
            if current_attempt > max_retries:
                # Fallback to conversational explanation from the LLM
                try:
                    conv_response = await provider.generate(
                        question,
                        system_prompt=(
                            "You are QuantiText's intelligent Business Intelligence assistant. "
                            "If the user is asking a conversational question, greeting, or concept question (like EOQ, MAPE, safety stock), "
                            "answer clearly and politely in 2-4 sentences. "
                            "Explain what metrics they can ask about: daily sales/revenue, top products, region breakdowns, inventory health, demand forecasts, and anomalies. "
                            "Do not mention internal database errors."
                        ),
                        task_type=TaskType.GENERAL,
                        temperature=0.3,
                    )
                    answer = conv_response.text
                except Exception:
                    answer = (
                        "I couldn't generate a database query for that question. "
                        "You can ask about daily revenue, top products, low stock items, or detected anomalies."
                    )
                sql = None
        except Exception as e:
            last_error = f"Execution error: {e}"
            log.warning("SQL execution attempt %d failed: %s", current_attempt, e)
            current_attempt += 1
            if current_attempt > max_retries:
                try:
                    conv_response = await provider.generate(
                        question,
                        system_prompt=(
                            "You are QuantiText's intelligent Business Intelligence assistant. "
                            "Answer the user's question politely and suggest they try asking with a specific metric like revenue, products, or inventory."
                        ),
                        task_type=TaskType.GENERAL,
                        temperature=0.3,
                    )
                    answer = conv_response.text
                except Exception:
                    answer = "The query ran into an issue. Please try rephrasing with a specific metric such as revenue or stock."

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
    return [
        {"role": r["role"], "content": r["content"], "timestamp": r["created_at"]} for r in rows
    ]


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
        {
            "id": str(uuid.uuid4()),
            "session_id": str(session_id),
            "org_id": org_id,
            "content": question,
        },
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
        {
            "id": str(uuid.uuid4()),
            "session_id": str(session_id),
            "org_id": org_id,
            "content": assistant_content,
        },
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


def _format_result_for_llm(
    columns: list[str],
    rows: list[list],
    total_row_count: int | None = None,
) -> str:
    """
    Format query results as compact aggregated summaries for the LLM.
    Guarantees no customer PII is sent, adhering to AGENTS.md requirements:
    - Never send customer-level or PII data to the LLM. Only aggregated figures.
    - Capped at maximum 10 preview rows.
    """
    if not rows:
        return "No rows returned."

    count = total_row_count if total_row_count is not None else len(rows)
    preview = rows[:10]

    # Redact any customer/PII columns if present
    pii_keywords = {"customer", "email", "phone", "first_name", "last_name", "address", "ssn"}
    masked_indices = set()
    safe_columns = []
    for idx, col in enumerate(columns):
        col_lower = col.lower()
        if any(k in col_lower for k in pii_keywords) and col_lower not in {
            "product_name",
            "category_name",
            "unique_customers",
        }:
            masked_indices.add(idx)
            safe_columns.append(f"{col} [ANONYMIZED]")
        else:
            safe_columns.append(col)

    safe_rows = []
    for row in preview:
        safe_r = []
        for idx, val in enumerate(row):
            if idx in masked_indices:
                safe_r.append("[REDACTED]")
            else:
                safe_r.append(str(val))
        safe_rows.append(safe_r)

    header = " | ".join(safe_columns)
    separator = "-" * len(header)
    data_rows = "\n".join(" | ".join(r) for r in safe_rows)

    summary_header = f"Result Summary: {count} total rows returned."
    if count > len(preview):
        summary_header += f" (Showing first {len(preview)} aggregated rows)"

    return f"{summary_header}\n\n{header}\n{separator}\n{data_rows}"


def _infer_chart_type(question: str, columns: list[str], row_count: int = 2) -> str | None:
    """Heuristic: infer chart type from question, columns, and row count."""
    if row_count <= 1:
        return "table"

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
        suggestions.extend(
            [
                "Which product category drove the most growth?",
                "How does this compare to the previous period?",
            ]
        )
    elif "stock" in q or "inventory" in q:
        suggestions.extend(
            [
                "Which products need immediate reordering?",
                "What is the total inventory value at risk?",
            ]
        )
    elif "top" in q or "product" in q:
        suggestions.extend(
            [
                "Show me the revenue trend for the top product",
                "Which region drives the most sales for these products?",
            ]
        )

    if result and result.get("row_count", 0) > 0:
        suggestions.append("Export this data as a report")

    return suggestions[:3]
