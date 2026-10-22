"""
Offline Fallback LLM Provider.

Provides robust, zero-downtime offline NL2SQL and query summarization when
external LLMs (Gemini / Ollama) are not connected or configured.
Translates business intelligence questions directly into secure, read-only
PostgreSQL queries against views and pre-aggregated analytics tables.
"""

from __future__ import annotations

import logging
import re

from app.services.llm.base import LLMProvider, LLMResponse, TaskType

log = logging.getLogger(__name__)


class OfflineFallbackProvider(LLMProvider):
    """
    Offline NL2SQL & BI narrative generator.
    Guarantees the system operates cleanly in demo/presentation environments
    without throwing 500 errors, connection timeouts, or returning repetitive responses.
    """

    @property
    def provider_name(self) -> str:
        return "offline_fallback"

    @property
    def is_available(self) -> bool:
        return True

    async def generate_sql(
        self,
        question: str,
        *,
        schema_context: str,
        examples: list[dict] | None = None,
        dialect: str = "postgresql",
    ) -> LLMResponse:
        """Heuristically generate an optimized read-only SQL query from the natural question."""
        q = question.lower().strip()
        words = set(re.findall(r"\b\w+\b", q))

        # Check for temporal indicators
        has_today = "today" in words or "current" in words
        has_yesterday = "yesterday" in words
        days_match = re.search(r"\b(?:last|past|previous)\s+(\d+)\s+days?\b", q)
        num_days = int(days_match.group(1)) if days_match else None
        has_month = "month" in words
        has_week = "week" in words

        # Check for intent
        wants_trend = (
            any(w in words for w in ["trend", "daily", "chart", "breakdown", "over_time", "by_day"])
            or "per day" in q
            or "by day" in q
        )

        # 1. Product specific queries
        if any(w in words for w in ["product", "products", "item", "items", "sku", "skus"]):
            limit = 5
            match = re.search(r"\b(\d+)\b", q)
            if match:
                limit = min(50, int(match.group(1)))
            order_col = (
                "total_qty"
                if any(w in words for w in ["volume", "qty", "quantity", "units"])
                else "total_revenue"
            )
            sort_dir = (
                "ASC" if any(w in words for w in ["worst", "lowest", "bottom", "least"]) else "DESC"
            )
            sql = (
                f"SELECT p.sku, p.name AS product_name, c.name AS category_name, "
                f"SUM(ds.quantity_sold) AS total_qty, ROUND(SUM(ds.revenue)::numeric, 2) AS total_revenue "
                f"FROM daily_sales ds "
                f"JOIN products p ON p.id = ds.product_id "
                f"LEFT JOIN categories c ON c.id = p.category_id "
                f"WHERE ds.org_id = '<org_id>' "
                f"GROUP BY p.sku, p.name, c.name "
                f"ORDER BY {order_col} {sort_dir} LIMIT {limit};"
            )

        # 2. Inventory / Stock
        elif any(
            w in words for w in ["stock", "inventory", "reorder", "runout", "critical", "overstock"]
        ):
            if "overstock" in words:
                sql = (
                    "SELECT sku, product_name, category_name, stock_on_hand, reorder_point, status_label "
                    "FROM v_inventory_status "
                    "WHERE org_id = '<org_id>' AND status_label = 'overstock' "
                    "ORDER BY stock_on_hand DESC LIMIT 15;"
                )
            else:
                sql = (
                    "SELECT sku, product_name, category_name, stock_on_hand, reorder_point, "
                    "lead_time_days, status_label "
                    "FROM v_inventory_status "
                    "WHERE org_id = '<org_id>' "
                    "ORDER BY stock_on_hand ASC LIMIT 10;"
                )

        # 3. Category performance
        elif any(w in words for w in ["category", "categories"]):
            limit = 5
            match = re.search(r"\b(\d+)\b", q)
            if match:
                limit = min(20, int(match.group(1)))
            order_col = (
                "total_volume"
                if any(w in words for w in ["volume", "qty", "quantity", "units"])
                else "total_revenue"
            )
            sql = (
                f"SELECT c.name AS category_name, SUM(ds.quantity_sold) AS total_volume, "
                f"ROUND(SUM(ds.revenue)::numeric, 2) AS total_revenue, "
                f"ROUND((SUM(ds.revenue) * 0.35)::numeric, 2) AS estimated_profit "
                f"FROM daily_sales ds "
                f"JOIN products p ON p.id = ds.product_id "
                f"JOIN categories c ON c.id = p.category_id "
                f"WHERE ds.org_id = '<org_id>' "
                f"GROUP BY c.name "
                f"ORDER BY {order_col} DESC LIMIT {limit};"
            )

        # 4. Regional breakdown
        elif any(w in words for w in ["region", "regions", "country", "geographic", "territory"]):
            sql = (
                "SELECT region, ROUND(SUM(total_revenue)::numeric, 2) AS total_revenue, "
                "ROUND((SUM(total_revenue) * 0.35)::numeric, 2) AS estimated_profit, "
                "SUM(total_qty) AS total_units_sold, "
                "ROUND((SUM(total_revenue) / NULLIF(SUM(total_qty), 0))::numeric, 2) AS avg_revenue_per_unit "
                "FROM v_sales_by_region "
                "WHERE org_id = '<org_id>' "
                "GROUP BY region "
                "ORDER BY total_revenue DESC;"
            )

        # 5. Anomalies & Spikes & Alerts
        elif any(
            w in words
            for w in [
                "anomal",
                "anomalies",
                "spike",
                "drop",
                "alert",
                "alerts",
                "outlier",
                "outliers",
            ]
        ):
            sql = (
                "SELECT a.detected_date, a.anomaly_type, a.detector, ROUND(a.severity_score::numeric, 3) AS severity_score, "
                "ROUND(COALESCE(a.estimated_impact, 0)::numeric, 2) AS estimated_impact, p.sku, p.name AS product_name "
                "FROM anomalies a "
                "JOIN products p ON p.id = a.product_id "
                "WHERE a.org_id = '<org_id>' "
                "ORDER BY a.detected_date DESC, a.severity_score DESC LIMIT 10;"
            )

        # 6. Forecasts
        elif any(
            w in words for w in ["forecast", "forecasts", "predict", "predictions", "projection"]
        ):
            sql = (
                "SELECT f.forecast_date, p.sku, p.name AS product_name, "
                "ROUND(f.predicted_qty::numeric, 1) AS predicted_qty, "
                "ROUND(f.lower_bound::numeric, 1) AS lower_bound, "
                "ROUND(f.upper_bound::numeric, 1) AS upper_bound, f.model_name "
                "FROM forecasts f "
                "JOIN products p ON p.id = f.product_id "
                "WHERE f.org_id = '<org_id>' "
                "ORDER BY f.forecast_date ASC LIMIT 15;"
            )

        # 7. Recommendations
        elif any(
            w in words
            for w in [
                "recommend",
                "recommendation",
                "recommendations",
                "action",
                "actions",
                "approval",
                "decision",
            ]
        ):
            sql = (
                "SELECT action_type, reason, status, created_at "
                "FROM recommendations "
                "WHERE org_id = '<org_id>' "
                "ORDER BY created_at DESC LIMIT 6;"
            )

        # 8. TODAY Revenue / Profit
        elif has_today:
            sql = (
                "SELECT sale_date, ROUND(total_revenue::numeric, 2) AS total_revenue, "
                "ROUND((total_revenue * 0.35)::numeric, 2) AS estimated_profit, "
                "order_count, ROUND(avg_order_value::numeric, 2) AS avg_order_value "
                "FROM v_kpi_daily "
                "WHERE org_id = '<org_id>' "
                "AND sale_date = (SELECT MAX(sale_date) FROM v_kpi_daily WHERE org_id = '<org_id>') "
                "LIMIT 1;"
            )

        # 9. YESTERDAY Revenue / Profit
        elif has_yesterday:
            sql = (
                "SELECT sale_date, ROUND(total_revenue::numeric, 2) AS total_revenue, "
                "ROUND((total_revenue * 0.35)::numeric, 2) AS estimated_profit, "
                "order_count, ROUND(avg_order_value::numeric, 2) AS avg_order_value "
                "FROM v_kpi_daily "
                "WHERE org_id = '<org_id>' "
                "AND sale_date = (SELECT MAX(sale_date) FROM v_kpi_daily WHERE org_id = '<org_id>') - INTERVAL '1 day' "
                "LIMIT 1;"
            )

        # 10. LAST N DAYS (Aggregate total vs Daily trend)
        elif num_days is not None:
            if wants_trend:
                sql = (
                    f"SELECT sale_date, ROUND(total_revenue::numeric, 2) AS total_revenue, "
                    f"ROUND((total_revenue * 0.35)::numeric, 2) AS estimated_profit, "
                    f"order_count, ROUND(avg_order_value::numeric, 2) AS avg_order_value "
                    f"FROM v_kpi_daily "
                    f"WHERE org_id = '<org_id>' "
                    f"AND sale_date >= (SELECT MAX(sale_date) FROM v_kpi_daily WHERE org_id = '<org_id>') - INTERVAL '{num_days} days' "
                    f"ORDER BY sale_date DESC LIMIT {num_days};"
                )
            else:
                sql = (
                    f"SELECT ROUND(SUM(total_revenue)::numeric, 2) AS total_revenue, "
                    f"ROUND((SUM(total_revenue) * 0.35)::numeric, 2) AS estimated_profit, "
                    f"SUM(order_count) AS total_orders, "
                    f"ROUND(AVG(avg_order_value)::numeric, 2) AS avg_order_value, "
                    f"SUM(unique_customers) AS unique_customers "
                    f"FROM v_kpi_daily "
                    f"WHERE org_id = '<org_id>' "
                    f"AND sale_date >= (SELECT MAX(sale_date) FROM v_kpi_daily WHERE org_id = '<org_id>') - INTERVAL '{num_days} days';"
                )

        # 11. THIS MONTH (Aggregate vs Daily trend)
        elif has_month:
            if wants_trend:
                sql = (
                    "SELECT sale_date, ROUND(total_revenue::numeric, 2) AS total_revenue, "
                    "ROUND((total_revenue * 0.35)::numeric, 2) AS estimated_profit, "
                    "order_count, ROUND(avg_order_value::numeric, 2) AS avg_order_value "
                    "FROM v_kpi_daily "
                    "WHERE org_id = '<org_id>' "
                    "AND sale_date >= DATE_TRUNC('month', (SELECT MAX(sale_date) FROM v_kpi_daily WHERE org_id = '<org_id>')) "
                    "ORDER BY sale_date DESC LIMIT 31;"
                )
            else:
                sql = (
                    "SELECT ROUND(SUM(total_revenue)::numeric, 2) AS total_revenue, "
                    "ROUND((SUM(total_revenue) * 0.35)::numeric, 2) AS estimated_profit, "
                    "SUM(order_count) AS total_orders, "
                    "ROUND(AVG(avg_order_value)::numeric, 2) AS avg_order_value, "
                    "SUM(unique_customers) AS unique_customers "
                    "FROM v_kpi_daily "
                    "WHERE org_id = '<org_id>' "
                    "AND sale_date >= DATE_TRUNC('month', (SELECT MAX(sale_date) FROM v_kpi_daily WHERE org_id = '<org_id>'));"
                )

        # 12. THIS WEEK / LAST WEEK
        elif has_week:
            if wants_trend:
                sql = (
                    "SELECT sale_date, ROUND(total_revenue::numeric, 2) AS total_revenue, "
                    "ROUND((total_revenue * 0.35)::numeric, 2) AS estimated_profit, "
                    "order_count, ROUND(avg_order_value::numeric, 2) AS avg_order_value "
                    "FROM v_kpi_daily "
                    "WHERE org_id = '<org_id>' "
                    "AND sale_date >= (SELECT MAX(sale_date) FROM v_kpi_daily WHERE org_id = '<org_id>') - INTERVAL '7 days' "
                    "ORDER BY sale_date DESC LIMIT 7;"
                )
            else:
                sql = (
                    "SELECT ROUND(SUM(total_revenue)::numeric, 2) AS total_revenue, "
                    "ROUND((SUM(total_revenue) * 0.35)::numeric, 2) AS estimated_profit, "
                    "SUM(order_count) AS total_orders, "
                    "ROUND(AVG(avg_order_value)::numeric, 2) AS avg_order_value, "
                    "SUM(unique_customers) AS unique_customers "
                    "FROM v_kpi_daily "
                    "WHERE org_id = '<org_id>' "
                    "AND sale_date >= (SELECT MAX(sale_date) FROM v_kpi_daily WHERE org_id = '<org_id>') - INTERVAL '7 days';"
                )

        # 13. GENERAL TREND
        elif wants_trend:
            sql = (
                "SELECT sale_date, ROUND(total_revenue::numeric, 2) AS total_revenue, "
                "ROUND((total_revenue * 0.35)::numeric, 2) AS estimated_profit, "
                "order_count, ROUND(avg_order_value::numeric, 2) AS avg_order_value "
                "FROM v_kpi_daily "
                "WHERE org_id = '<org_id>' "
                "ORDER BY sale_date DESC LIMIT 30;"
            )

        # 14. OVERALL / DEFAULT (Aggregate total)
        else:
            sql = (
                "SELECT ROUND(SUM(total_revenue)::numeric, 2) AS total_revenue, "
                "ROUND((SUM(total_revenue) * 0.35)::numeric, 2) AS estimated_profit, "
                "SUM(order_count) AS total_orders, "
                "ROUND(AVG(avg_order_value)::numeric, 2) AS avg_order_value, "
                "SUM(unique_customers) AS unique_customers "
                "FROM v_kpi_daily "
                "WHERE org_id = '<org_id>';"
            )

        return LLMResponse(
            text=sql,
            prompt_tokens=len(question.split()),
            completion_tokens=len(sql.split()),
            total_tokens=len(question.split()) + len(sql.split()),
            provider=self.provider_name,
            model="offline-heuristic-v2",
        )

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        context: list[dict] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        task_type: TaskType = TaskType.GENERAL,
    ) -> LLMResponse:
        """Grounded synthesis from executed query results or context data."""
        if "Query Result:" in prompt:
            parts = prompt.split("Query Result:")
            question_text = parts[0].replace("Question:", "").strip()
            result_part = parts[1].strip().split("\n\nProvide")[0].strip()

            raw_lines = [line.strip() for line in result_part.splitlines() if line.strip()]
            if not raw_lines or raw_lines[0] == "No results.":
                ans = "The database query executed successfully, but no matching records were found for that criteria."
                return LLMResponse(
                    text=ans,
                    prompt_tokens=len(prompt.split()),
                    completion_tokens=len(ans.split()),
                    total_tokens=len(prompt.split()) + len(ans.split()),
                    provider=self.provider_name,
                    model="offline-heuristic-v2",
                )

            headers = [h.strip() for h in raw_lines[0].split("|")]
            # Filter out separator lines (e.g. "----------------------")
            data_rows = [
                [c.strip() for c in line.split("|")]
                for line in raw_lines[1:]
                if not line.startswith("-") and "|" in line
            ]

            q_lower = question_text.lower()
            q_words = set(re.findall(r"\b\w+\b", q_lower))
            wants_profit = any(w in q_words for w in ["profit", "margin", "margin_rate"])

            # ── Branch A: Single Row Summary (Aggregate or Today/Yesterday) ───────────
            if len(data_rows) == 1:
                row_map = dict(zip(headers, data_rows[0], strict=False))
                rev_val = row_map.get("total_revenue", "0")
                profit_val = row_map.get("estimated_profit", "0")
                orders_val = row_map.get("total_orders", row_map.get("order_count", "0"))
                aov_val = row_map.get("avg_order_value", "0")

                try:
                    rev_fmt = f"{float(rev_val):,.2f}"
                except Exception:
                    rev_fmt = rev_val

                try:
                    profit_fmt = f"{float(profit_val):,.2f}"
                except Exception:
                    profit_fmt = profit_val

                try:
                    aov_fmt = f"{float(aov_val):,.2f}"
                except Exception:
                    aov_fmt = aov_val

                if "sale_date" in row_map:
                    date_val = row_map["sale_date"]
                    if wants_profit:
                        ans = (
                            f"For **{date_val}**, estimated gross profit reached **£{profit_fmt}** "
                            f"(35% margin) on total revenue of **£{rev_fmt}** across **{orders_val}** customer orders "
                            f"(Average Order Value: **£{aov_fmt}**)."
                        )
                    else:
                        ans = (
                            f"For **{date_val}**, total revenue recorded was **£{rev_fmt}** across "
                            f"**{orders_val}** customer orders with an average order value of **£{aov_fmt}** "
                            f"(estimated profit: **£{profit_fmt}**)."
                        )
                else:
                    # Period aggregate (e.g. last 30 days, this month, overall)
                    period_match = re.search(r"\b(\d+)\s+days?\b", q_lower)
                    period_desc = (
                        f"last {period_match.group(1)} days" if period_match else "specified period"
                    )
                    if "month" in q_lower:
                        period_desc = "current month"

                    if wants_profit:
                        ans = (
                            f"Over the **{period_desc}**, estimated gross profit reached **£{profit_fmt}** "
                            f"on total revenue of **£{rev_fmt}** across **{orders_val}** orders "
                            f"(Average Order Value: **£{aov_fmt}**)."
                        )
                    else:
                        ans = (
                            f"Total revenue for the **{period_desc}** is **£{rev_fmt}** generated across "
                            f"**{orders_val}** customer orders, with an average order value of **£{aov_fmt}** "
                            f"(estimated gross profit: **£{profit_fmt}**)."
                        )

            # ── Branch B: Time Series / Daily Trend (Multi-row) ────────────────────────
            elif "sale_date" in headers and len(data_rows) > 1:
                n_days = len(data_rows)
                start_date = data_rows[-1][0]
                end_date = data_rows[0][0]

                rev_idx = headers.index("total_revenue") if "total_revenue" in headers else 1
                try:
                    revs = [float(r[rev_idx]) for r in data_rows if len(r) > rev_idx]
                    total_rev = sum(revs)
                    avg_rev = total_rev / max(1, len(revs))
                    max_rev = max(revs)
                    max_row = next(r for r in data_rows if float(r[rev_idx]) == max_rev)
                    peak_date = max_row[0]
                except Exception:
                    total_rev = 0
                    avg_rev = 0
                    max_rev = 0
                    peak_date = end_date

                total_profit = total_rev * 0.35

                if wants_profit:
                    ans = (
                        f"Across the **{n_days}** days from **{start_date}** to **{end_date}**, "
                        f"total estimated gross profit reached **£{total_profit:,.2f}** "
                        f"(35% margin on **£{total_rev:,.2f}** revenue). "
                        f"Peak daily performance was on **{peak_date}** with **£{max_rev * 0.35:,.2f}** profit."
                    )
                else:
                    ans = (
                        f"Daily sales trend across **{n_days}** days ({start_date} to {end_date}) "
                        f"totaled **£{total_rev:,.2f}** in revenue, averaging **£{avg_rev:,.2f}**/day. "
                        f"Peak sales occurred on **{peak_date}** at **£{max_rev:,.2f}**."
                    )

            # ── Branch C: Products ──────────────────────────────────────────────────
            elif any(k in headers for k in ["product_name", "sku"]):
                top_items = []
                for r in data_rows[:3]:
                    if len(r) >= 2:
                        top_items.append(f"**{r[0]}** ({r[1]})")
                joined = ", ".join(top_items)
                ans = (
                    f"Top-performing products identified from transactional records are {joined}. "
                    f"These catalog items generate the strongest volume and turnover."
                )

            # ── Branch D: Inventory / Stock ──────────────────────────────────────────
            elif any(k in headers for k in ["stock_on_hand", "status_label"]):
                top_item = data_rows[0]
                ans = (
                    f"Inventory inspection identified **{len(data_rows)}** items currently monitored, "
                    f"led by **{top_item[0]}** ({top_item[1]}) with **{top_item[3]}** units in stock "
                    f"against a reorder point of **{top_item[4]}**."
                )

            # ── Branch E: Regions ────────────────────────────────────────────────────
            elif "region" in headers:
                top_region = data_rows[0][0]
                top_rev = data_rows[0][1]
                ans = (
                    f"Regional distribution shows **{len(data_rows)}** fulfillment territories. "
                    f"**{top_region}** leads with **£{float(top_rev):,.2f}** in revenue."
                )

            # ── Branch F: Categories ─────────────────────────────────────────────────
            elif "category_name" in headers:
                top_cat = data_rows[0][0]
                top_vol = data_rows[0][1]
                top_rev = data_rows[0][2] if len(data_rows[0]) > 2 else "0"
                ans = (
                    f"Category breakdown across **{len(data_rows)}** categories is led by **{top_cat}** "
                    f"with **{top_vol}** units sold (**£{float(top_rev):,.2f}** total revenue)."
                )

            # ── Branch G: Anomalies ──────────────────────────────────────────────────
            elif "anomaly_type" in headers:
                top_a = data_rows[0]
                ans = (
                    f"Detected **{len(data_rows)}** anomaly events. Top alert: **{top_a[1]}** "
                    f"detected on **{top_a[0]}** (severity score: **{top_a[3]}**)."
                )

            # ── Branch H: General / Default ──────────────────────────────────────────
            else:
                ans = f"Retrieved {len(data_rows)} active records matching your analysis criteria."

        else:
            ans = "The system executed your analytical query against the database and retrieved live figures."

        return LLMResponse(
            text=ans,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(ans.split()),
            total_tokens=len(prompt.split()) + len(ans.split()),
            provider=self.provider_name,
            model="offline-heuristic-v2",
        )
