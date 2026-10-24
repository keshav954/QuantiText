"""
Tests for copilot service — SQL validation and injection prevention.
"""

from __future__ import annotations

import pytest

from app.services.copilot_service import (
    _infer_chart_type,
    _inject_org_id,
    _validate_sql,
    validate_and_secure_sql,
)

# ── SQL validation ──────────────────────────────────────────────────────────────


def test_validate_and_secure_sql_valid():
    sql = "SELECT sku, total_revenue FROM v_sales_by_product WHERE org_id = '<org_id>'"
    secured = validate_and_secure_sql(sql, "11111111-1111-1111-1111-111111111111")
    assert "11111111-1111-1111-1111-111111111111" in secured
    assert "v_sales_by_product" in secured


def test_validate_and_secure_sql_injects_missing_org():
    sql = "SELECT * FROM v_kpi_daily WHERE sale_date >= CURRENT_DATE"
    secured = validate_and_secure_sql(sql, "11111111-1111-1111-1111-111111111111")
    assert "org_id = '11111111-1111-1111-1111-111111111111'" in secured


def test_validate_and_secure_sql_blocks_unauthorized_table():
    sql = "SELECT * FROM users WHERE org_id = '<org_id>'"
    with pytest.raises(ValueError, match="not permitted"):
        validate_and_secure_sql(sql, "11111111-1111-1111-1111-111111111111")


def test_validate_and_secure_sql_blocks_functions():
    sql = "SELECT pg_sleep(5) FROM v_kpi_daily WHERE org_id = '<org_id>'"
    with pytest.raises(ValueError, match="blocked"):
        validate_and_secure_sql(sql, "11111111-1111-1111-1111-111111111111")


def test_validate_and_secure_sql_with_cte():
    sql = "WITH monthly AS (SELECT * FROM v_kpi_daily) SELECT * FROM monthly"
    secured = validate_and_secure_sql(sql, "11111111-1111-1111-1111-111111111111")
    assert "WITH monthly AS" in secured
    assert "11111111-1111-1111-1111-111111111111" in secured


def test_validate_and_secure_sql_with_conversational_wrapping():
    sql = "Here is the SQL query you requested:\n```sql\nSELECT * FROM v_kpi_daily\n```\nHope this helps!"
    secured = validate_and_secure_sql(sql, "11111111-1111-1111-1111-111111111111")
    assert "SELECT" in secured
    assert "v_kpi_daily" in secured


def test_validate_and_secure_sql_supporting_tables():
    sql = "SELECT p.name, c.name FROM products p JOIN categories c ON p.category_id = c.id"
    secured = validate_and_secure_sql(sql, "11111111-1111-1111-1111-111111111111")
    assert "products" in secured
    assert "categories" in secured


def test_valid_select_passes():
    sql = "SELECT * FROM v_kpi_daily WHERE org_id = 'xxx' LIMIT 10"
    result = _validate_sql(sql)
    assert result.upper().startswith("SELECT")


def test_strips_markdown_fences():
    sql = "```sql\nSELECT 1\n```"
    result = _validate_sql(sql)
    assert result == "SELECT 1"


def test_strips_markdown_fences_no_lang():
    sql = "```\nSELECT 1\n```"
    result = _validate_sql(sql)
    assert result == "SELECT 1"


def test_rejects_insert():
    with pytest.raises(ValueError, match="not a SELECT"):
        _validate_sql("INSERT INTO users VALUES (1, 2)")


def test_rejects_delete():
    with pytest.raises(ValueError, match="not a SELECT"):
        _validate_sql("DELETE FROM users")


def test_rejects_drop():
    with pytest.raises(ValueError, match="Dangerous"):
        _validate_sql("SELECT 1; DROP TABLE users")


def test_rejects_update_in_cte():
    """UPDATE inside a seemingly valid query must be caught."""
    with pytest.raises(ValueError):
        _validate_sql("SELECT id FROM (UPDATE users SET role='admin' RETURNING id) t")


def test_rejects_exec():
    with pytest.raises(ValueError, match="Dangerous"):
        _validate_sql("SELECT 1; EXEC sp_executesql('DROP TABLE x')")


def test_org_id_injection():
    sql = "SELECT * FROM v_kpi_daily WHERE org_id = '<org_id>'"
    result = _inject_org_id(sql, "my-org-uuid")
    assert "'my-org-uuid'" in result
    assert "<org_id>" not in result


def test_org_id_injection_quoted():
    sql = "SELECT * FROM v_kpi_daily WHERE org_id = '<org_id>'"
    result = _inject_org_id(sql, "abc-123")
    assert result == "SELECT * FROM v_kpi_daily WHERE org_id = 'abc-123'"


# ── Chart type inference ────────────────────────────────────────────────────────


def test_infer_line_chart_from_question():
    assert _infer_chart_type("show daily revenue trend", ["sale_date", "revenue"]) == "line"


def test_infer_bar_chart_top():
    assert _infer_chart_type("top 10 products by revenue", ["product", "revenue"]) == "bar"


def test_infer_pie_breakdown():
    assert _infer_chart_type("breakdown by category", ["category", "revenue"]) == "pie"


def test_infer_line_from_date_column():
    assert _infer_chart_type("give me the numbers", ["date", "value"]) == "line"


def test_infer_table_fallback():
    assert _infer_chart_type("how many users", ["user_count"]) == "table"
