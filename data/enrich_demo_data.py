"""
Enrichment script — adds rich, realistic presentation data to the QuantiText database:
- Multiple demo users across RBAC roles (admin, manager, analyst, viewer)
- Additional anomalies and alerts across all categories
- Closed-loop decision recommendations (pending, approved, rejected)
- Interactive Copilot conversation threads with SQL queries, tables, and AI responses
- Customer feedback records for hybrid search and sentiment analytics
- Executive BI reports with grounded narratives

Usage:
    python -m data.enrich_demo_data
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg2://quantitext:changeme_dev_only@localhost:5432/quantitext",
)

NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def stable_uuid(name: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, name)


def enrich_data() -> None:
    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        # Check org
        result = session.execute(text("SELECT id FROM orgs LIMIT 1"))
        row = result.first()
        if not row:
            log.error("No organization found. Please run 'python -m data.seed' first.")
            return

        org_id = row[0]
        log.info("Enriching database for org_id=%s...", org_id)

        # Get existing products
        prod_rows = session.execute(
            text(
                "SELECT id, sku, name FROM products WHERE org_id = :org_id ORDER BY sku LIMIT 30"
            ),
            {"org_id": str(org_id)},
        ).fetchall()
        if not prod_rows:
            log.error("No products found to attach demo data to.")
            return

        today = date.today()
        now_dt = datetime.now(UTC)

        # ── 1. Demo Users (RBAC) ─────────────────────────────────
        log.info("Creating demo users across RBAC roles...")
        try:
            from app.core.security import hash_password

            def get_hash(p: str) -> str:
                return hash_password(p)
        except Exception:  # noqa: BLE001
            # Fallback pre-computed argon2 hashes for dev passwords
            def get_hash(p: str) -> str:
                return "$argon2id$v=19$m=65536,t=3,p=4$aos+yPaeP1sTX2QTmi7l1w$uVbhovRHYTukKXwM+PFN3IzJblUzXMPgORaxFYdaHC4"

        users = [
            ("admin@demo.local", "admin123", "Admin User", "admin"),
            ("manager@demo.local", "manager123", "Operational Manager", "manager"),
            ("analyst@demo.local", "analyst123", "BI Data Analyst", "analyst"),
            ("viewer@demo.local", "viewer123", "Executive Viewer", "viewer"),
        ]

        user_map = {}
        for email, pwd, name, role in users:
            uid = stable_uuid(f"user-{email}")
            user_map[role] = uid
            session.execute(
                text("""
                    INSERT INTO users (id, org_id, email, hashed_password, full_name, role, is_active)
                    VALUES (:id, :org_id, :email, :hash, :name, :role, true)
                    ON CONFLICT (email) DO UPDATE SET
                        role = EXCLUDED.role,
                        full_name = EXCLUDED.full_name,
                        is_active = true
                """),
                {
                    "id": str(uid),
                    "org_id": str(org_id),
                    "email": email,
                    "hash": get_hash(pwd),
                    "name": name,
                    "role": role,
                },
            )
        session.commit()
        log.info(
            "Upserted %d demo users with roles (admin, manager, analyst, viewer)",
            len(users),
        )

        # Fetch actual DB user IDs to ensure foreign keys match exactly
        user_rows = session.execute(
            text("SELECT role, id FROM users WHERE org_id = :org_id"),
            {"org_id": str(org_id)},
        ).fetchall()
        user_map = {r[0]: str(r[1]) for r in user_rows}

        admin_id = user_map.get("admin")
        manager_id = user_map.get("manager")

        # ── 2. Anomalies & Alerts ────────────────────────────────
        log.info("Adding rich anomalies and alert notifications...")
        anomalies_specs = [
            (
                0,
                "revenue_spike",
                "zscore",
                0.92,
                3120.00,
                1,
                "Viral marketing campaign surge",
                {
                    "zscore": 4.12,
                    "baseline": 520.0,
                    "actual": 3640.0,
                    "region": "Europe",
                },
            ),
            (
                1,
                "revenue_drop",
                "iforest",
                0.89,
                -4200.00,
                2,
                "Supplier component shortage / stockout",
                {
                    "anomaly_score": -0.48,
                    "baseline_units": 80,
                    "actual_units": 5,
                    "region": "Europe",
                },
            ),
            (
                2,
                "zero_sales",
                "data_quality",
                0.75,
                -1450.00,
                3,
                "Catalog URL 404 broken link",
                {"streak_days": 4, "expected_daily_qty": 22, "impact_pct": "-100%"},
            ),
            (
                3,
                "inventory_critical",
                "zscore",
                0.85,
                -2100.00,
                1,
                "Runout danger (<24h cover)",
                {"current_stock": 3, "reorder_point": 55, "days_of_supply": 0.4},
            ),
            (
                4,
                "revenue_spike",
                "iforest",
                0.68,
                1250.00,
                2,
                "B2B bulk commercial order",
                {"anomaly_score": -0.28, "baseline": 300.0, "actual": 1550.0},
            ),
            (
                5,
                "revenue_drop",
                "zscore",
                0.78,
                -1890.00,
                4,
                "Regional distribution center shipping halt",
                {"zscore": -3.15, "baseline_revenue": 890.0, "actual_revenue": 120.0},
            ),
            (
                6,
                "inventory_critical",
                "data_quality",
                0.82,
                -1650.00,
                2,
                "Holding cost spike due to overstock",
                {"excess_units": 450, "carrying_cost_annual": 3200.0},
            ),
            (
                7,
                "revenue_spike",
                "zscore",
                0.73,
                980.00,
                5,
                "Flash weekend promotion clearance",
                {"zscore": 2.92, "lift": "+320%"},
            ),
            (
                8,
                "zero_sales",
                "data_quality",
                0.60,
                -820.00,
                6,
                "Payment gateway checkout friction",
                {"failed_checkouts": 35, "region": "Americas"},
            ),
            (
                9,
                "revenue_drop",
                "iforest",
                0.71,
                -1350.00,
                3,
                "Competitor price drop elasticity",
                {"volume_shift": "-45%", "region": "Asia-Pacific"},
            ),
        ]

        for (
            idx,
            anom_type,
            detector,
            sev,
            impact,
            days_ago,
            desc,
            details,
        ) in anomalies_specs:
            prod = prod_rows[idx % len(prod_rows)]
            anom_id = stable_uuid(f"anom-rich-{idx}-{prod[1]}")
            det_date = today - timedelta(days=days_ago)

            session.execute(
                text("""
                    INSERT INTO anomalies (id, org_id, product_id, detected_date, anomaly_type,
                                           detector, severity_score, estimated_impact, details, is_dismissed, created_at)
                    VALUES (:id, :org_id, :prod_id, :det_date, :type, :detector,
                            :sev, :impact, :details, false, :created_at)
                    ON CONFLICT (id) DO UPDATE SET
                        severity_score = EXCLUDED.severity_score,
                        estimated_impact = EXCLUDED.estimated_impact,
                        details = EXCLUDED.details
                """),
                {
                    "id": str(anom_id),
                    "org_id": str(org_id),
                    "prod_id": str(prod[0]),
                    "det_date": det_date,
                    "type": anom_type,
                    "detector": detector,
                    "sev": sev,
                    "impact": impact,
                    "details": json.dumps(details),
                    "created_at": now_dt - timedelta(days=days_ago),
                },
            )

            # Corresponding Alert
            alert_sev = (
                "critical" if sev >= 0.80 else ("warning" if sev >= 0.65 else "info")
            )
            alert_id = stable_uuid(f"alert-rich-{idx}-{prod[1]}")
            session.execute(
                text("""
                    INSERT INTO alerts (id, org_id, anomaly_id, title, description, severity, is_read, created_at)
                    VALUES (:id, :org_id, :anom_id, :title, :desc, :sev, false, :created_at)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        severity = EXCLUDED.severity
                """),
                {
                    "id": str(alert_id),
                    "org_id": str(org_id),
                    "anom_id": str(anom_id),
                    "title": f"[{alert_sev.upper()}] {desc} ({prod[1]})",
                    "desc": f"Automated detector ({detector}) flagged impact of £{impact:+,.2f} on {prod[2]}.",
                    "sev": alert_sev,
                    "created_at": now_dt - timedelta(days=days_ago),
                },
            )

        session.commit()
        log.info("Upserted 10 high-fidelity anomalies and alerts")

        # ── 3. Closed-Loop Recommendations ───────────────────────
        log.info("Adding closed-loop decision support recommendations...")
        recs = [
            (
                prod_rows[1][0],
                "reorder",
                "Critical stockout threat on primary velocity SKU. Expedite 180 units from primary UK distributor.",
                "pending",
                {
                    "suggested_qty": 180,
                    "lead_time_days": 7,
                    "urgency": "immediate",
                    "estimated_cost": 2160.00,
                    "supplier": "Apex Distribution",
                },
                None,
                None,
            ),
            (
                prod_rows[0][0],
                "investigate",
                "Sustained +510% demand surge observed. Adjust safety stock buffer from 20 to 65 units to capture projected upside.",
                "approved",
                {
                    "safety_stock_current": 20,
                    "safety_stock_proposed": 65,
                    "revenue_opportunity": 3120.00,
                },
                str(manager_id),
                now_dt - timedelta(hours=6),
            ),
            (
                prod_rows[2][0],
                "markdown",
                "Zero sales streak for 4 days with 340 units in warehouse. Run 15% markdown campaign to clear stock.",
                "pending",
                {
                    "discount_pct": 15,
                    "current_price": 32.00,
                    "promo_price": 27.20,
                    "estimated_recovery": 1450.00,
                },
                None,
                None,
            ),
            (
                prod_rows[3][0],
                "reorder",
                "Stock at 3 units (<24h cover). Replenish 120 units using calculated economic order quantity (EOQ).",
                "pending",
                {
                    "suggested_qty": 120,
                    "lead_time_days": 10,
                    "urgency": "immediate",
                    "estimated_cost": 1540.00,
                },
                None,
                None,
            ),
            (
                prod_rows[4][0],
                "investigate",
                "Single enterprise order accounted for 80% of weekly volume. Establish dedicated B2B wholesale pricing tier.",
                "approved",
                {
                    "target_account": "Enterprise Wholesale UK",
                    "volume_threshold": 100,
                    "margin_retention": "24%",
                },
                str(admin_id),
                now_dt - timedelta(days=1),
            ),
            (
                prod_rows[5][0],
                "reorder",
                "Regional distribution center stock rebalance. Transfer 75 units from Central Hub to Southern Depot.",
                "approved",
                {
                    "transfer_qty": 75,
                    "origin": "Central Hub",
                    "destination": "South Depot",
                    "transit_time_days": 2,
                },
                str(manager_id),
                now_dt - timedelta(days=2),
            ),
            (
                prod_rows[6][0],
                "markdown",
                "Overstocked inventory generating excessive carrying cost (£3,200 annual). Authorize 20% bundle discount.",
                "rejected",
                {
                    "reason_rejected": "Supplier contract specifies minimum advertised price (MAP) constraint."
                },
                str(admin_id),
                now_dt - timedelta(days=3),
            ),
            (
                prod_rows[7][0],
                "reorder",
                "Seasonal holiday buffer replenishment. Queue 250 units with standard 21-day oceanic freight schedule.",
                "pending",
                {
                    "suggested_qty": 250,
                    "lead_time_days": 21,
                    "urgency": "standard",
                    "estimated_cost": 3125.00,
                },
                None,
                None,
            ),
        ]

        for i, (
            prod_id,
            action,
            reason,
            status,
            params,
            approved_by,
            decided_at,
        ) in enumerate(recs):
            rec_id = stable_uuid(f"rec-rich-{i}-{prod_id}")
            session.execute(
                text("""
                    INSERT INTO recommendations (id, org_id, product_id, action_type, reason,
                                                 parameters, status, approved_by, decided_at, created_at)
                    VALUES (:id, :org_id, :prod_id, :action, :reason,
                            :params, :status, :approved_by, :decided_at, :created_at)
                    ON CONFLICT (id) DO UPDATE SET
                        reason = EXCLUDED.reason,
                        status = EXCLUDED.status,
                        parameters = EXCLUDED.parameters,
                        approved_by = EXCLUDED.approved_by,
                        decided_at = EXCLUDED.decided_at
                """),
                {
                    "id": str(rec_id),
                    "org_id": str(org_id),
                    "prod_id": str(prod_id),
                    "action": action,
                    "reason": reason,
                    "params": json.dumps(params),
                    "status": status,
                    "approved_by": approved_by,
                    "decided_at": decided_at,
                    "created_at": now_dt - timedelta(days=i, hours=2),
                },
            )
        session.commit()
        log.info("Upserted 8 closed-loop decision recommendations")

        # ── 4. Copilot Chat Sessions & History ───────────────────
        log.info("Populating pre-seeded Copilot chat sessions...")
        chat_threads = [
            {
                "title": "Top Revenue Categories & Product Drivers",
                "summary": "Analysis of category revenues showing Electronics leading at 45.2% share.",
                "messages": [
                    {
                        "role": "user",
                        "content": "Which 5 product categories generated the most revenue this year?",
                        "meta": {},
                    },
                    {
                        "role": "assistant",
                        "content": "Here are the top product categories by sales revenue based on transactional data:\n\n1. **Electronics**: £13,240,500 (45.2% share)\n2. **Clothing**: £6,810,200 (23.2% share)\n3. **Home & Garden**: £4,950,100 (16.8% share)\n4. **Sports**: £2,410,000 (8.2% share)\n5. **Food & Drink**: £1,986,800 (6.6% share)\n\nElectronics and Clothing continue to be our primary revenue pillars, contributing over 68% of total volume.",
                        "meta": {
                            "sql": "SELECT c.name AS category_name, SUM(ds.revenue) AS total_revenue FROM daily_sales ds JOIN products p ON p.id = ds.product_id JOIN categories c ON c.id = p.category_id GROUP BY c.name ORDER BY total_revenue DESC LIMIT 5;",
                            "chart_type": "bar",
                            "columns": ["category_name", "total_revenue"],
                            "rows": [
                                ["Electronics", 13240500],
                                ["Clothing", 6810200],
                                ["Home & Garden", 4950100],
                                ["Sports", 2410000],
                                ["Food & Drink", 1986800],
                            ],
                        },
                    },
                ],
            },
            {
                "title": "Critical Stockout Risks & Replenishment",
                "summary": "Identification of 4 SKUs with less than 24 hours of supply on hand.",
                "messages": [
                    {
                        "role": "user",
                        "content": "Which products currently have critical stock levels and need immediate reordering?",
                        "meta": {},
                    },
                    {
                        "role": "assistant",
                        "content": "I queried current inventory levels against dynamic reorder points. The following 4 SKUs are in **Critical** status with fewer than 2 days of supply remaining:\n\n- **SKU-0001**: 5 units on hand (Reorder point: 50, Lead time: 7 days)\n- **SKU-0003**: 3 units on hand (Reorder point: 55, Lead time: 10 days)\n- **SKU-0018**: 8 units on hand (Reorder point: 45, Lead time: 5 days)\n- **SKU-0042**: 4 units on hand (Reorder point: 40, Lead time: 14 days)\n\nAutomated purchase orders for these items have been generated and are awaiting approval in the **Reports & Approvals** tab.",
                        "meta": {
                            "sql": "SELECT p.sku, p.name AS product_name, i.stock_on_hand, i.reorder_point, i.lead_time_days FROM inventory i JOIN products p ON p.id = i.product_id WHERE i.stock_on_hand <= (i.reorder_point * 0.2) ORDER BY i.stock_on_hand ASC LIMIT 10;",
                            "chart_type": "table",
                            "columns": [
                                "sku",
                                "product_name",
                                "stock_on_hand",
                                "reorder_point",
                                "lead_time_days",
                            ],
                            "rows": [
                                ["SKU-0001", "Product-0001", 5, 50, 7],
                                ["SKU-0003", "Product-0003", 3, 55, 10],
                                ["SKU-0018", "Product-0018", 8, 45, 5],
                                ["SKU-0042", "Product-0042", 4, 40, 14],
                            ],
                        },
                    },
                ],
            },
            {
                "title": "Anomaly Root Cause: Viral Surge on SKU-0000",
                "summary": "Root cause analysis tracing +510% volume jump to regional marketing campaign.",
                "messages": [
                    {
                        "role": "user",
                        "content": "Explain the anomaly detected on SKU-0000 yesterday.",
                        "meta": {},
                    },
                    {
                        "role": "assistant",
                        "content": "### Anomaly Investigation: SKU-0000\n- **Type**: Revenue Spike (Z-Score: +4.12, Severity: 0.92)\n- **Impact**: +£3,120 estimated lift above trailing 30-day baseline.\n- **Root Cause**: An unexpected surge in European regional orders occurred following a verified digital marketing campaign on social channels. Daily demand jumped from an average of 480 units to 3,640 units.\n- **Recommended Action**: Approved safety stock increase from 20 to 65 units to prevent stockout over the next 14-day replenishment cycle.",
                        "meta": {
                            "anomaly_id": str(stable_uuid("anom-rich-0-SKU-0000")),
                            "chart_type": "line",
                        },
                    },
                ],
            },
        ]

        for s_idx, thread in enumerate(chat_threads):
            sess_id = stable_uuid(f"session-{s_idx}")
            session.execute(
                text("""
                    INSERT INTO chat_sessions (id, org_id, user_id, title, summary, created_at, updated_at)
                    VALUES (:id, :org_id, :uid, :title, :summary, :created_at, :updated_at)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        summary = EXCLUDED.summary
                """),
                {
                    "id": str(sess_id),
                    "org_id": str(org_id),
                    "uid": str(admin_id),
                    "title": thread["title"],
                    "summary": thread["summary"],
                    "created_at": now_dt - timedelta(days=s_idx + 1),
                    "updated_at": now_dt - timedelta(days=s_idx),
                },
            )

            for m_idx, msg in enumerate(thread["messages"]):
                msg_id = stable_uuid(f"msg-{s_idx}-{m_idx}")
                session.execute(
                    text("""
                        INSERT INTO chat_messages (id, session_id, org_id, role, content, metadata, created_at)
                        VALUES (:id, :sess_id, :org_id, :role, :content, :meta, :created_at)
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            metadata = EXCLUDED.metadata
                    """),
                    {
                        "id": str(msg_id),
                        "sess_id": str(sess_id),
                        "org_id": str(org_id),
                        "role": msg["role"],
                        "content": msg["content"],
                        "meta": json.dumps(msg["meta"]),
                        "created_at": now_dt
                        - timedelta(days=s_idx + 1, minutes=-10 * m_idx),
                    },
                )

        session.commit()
        log.info("Upserted 3 multi-turn Copilot chat sessions with queries & charts")

        # ── 5. Customer Feedback (Hybrid RAG) ────────────────────
        log.info("Adding customer reviews for feedback analytics...")
        customer_feedbacks = [
            (
                "review",
                5,
                "Outstanding build quality and arrived within 24 hours! Completely satisfied.",
                "positive",
                0.96,
                ["quality", "delivery"],
            ),
            (
                "review",
                4,
                "Great product. Package arrived slightly scuffed on the corners, but contents were fine.",
                "positive",
                0.62,
                ["packaging"],
            ),
            (
                "support_ticket",
                1,
                "Shipment delayed by 4 days without tracking updates. Terrible delivery experience.",
                "negative",
                -0.92,
                ["delivery", "tracking"],
            ),
            (
                "review",
                2,
                "Material feels significantly cheaper than advertised in photos. Requesting return.",
                "negative",
                -0.75,
                ["quality", "accuracy"],
            ),
            (
                "survey",
                5,
                "Repeat customer for 2 years. Pricing is competitive and fulfillment is always reliable.",
                "positive",
                0.94,
                ["price", "loyalty"],
            ),
            (
                "review",
                3,
                "Average item. Does what it says on the box, but customer service was slow to respond.",
                "neutral",
                0.05,
                ["support", "price"],
            ),
            (
                "review",
                5,
                "Exceptional performance! Best value purchase I have made in this category.",
                "positive",
                0.98,
                ["quality", "value"],
            ),
            (
                "support_ticket",
                2,
                "Received the incorrect size variation compared to my invoice order.",
                "negative",
                -0.68,
                ["fulfillment", "accuracy"],
            ),
            (
                "review",
                5,
                "Solid construction and very intuitive setup instructions.",
                "positive",
                0.88,
                ["usability", "quality"],
            ),
            (
                "review",
                4,
                "Good overall product. Would appreciate more color selections in future batches.",
                "positive",
                0.70,
                ["product_options"],
            ),
            (
                "support_ticket",
                1,
                "Defective unit out of the box. Power indicator won't turn on.",
                "negative",
                -0.95,
                ["defect", "quality"],
            ),
            (
                "survey",
                4,
                "Checkout flow was seamless. Delivery arrived right on the estimated time slot.",
                "positive",
                0.85,
                ["checkout", "delivery"],
            ),
        ]

        cust_row = session.execute(text("SELECT id FROM customers LIMIT 1")).first()
        cust_id = str(cust_row[0]) if cust_row else None

        for idx, (source, rating, text_content, sentiment, score, themes) in enumerate(
            customer_feedbacks
        ):
            fb_id = stable_uuid(f"feedback-rich-{idx}")
            prod = prod_rows[idx % len(prod_rows)]
            session.execute(
                text("""
                    INSERT INTO customer_feedback (id, org_id, product_id, customer_id, source, rating,
                                                   text_content, sentiment, sentiment_score, themes,
                                                   region, feedback_date, created_at)
                    VALUES (:id, :org_id, :prod_id, :cust_id, :source, :rating,
                            :text, :sentiment, :score, :themes, :region, :fb_date, :created_at)
                    ON CONFLICT (id) DO UPDATE SET
                        rating = EXCLUDED.rating,
                        text_content = EXCLUDED.text_content,
                        sentiment = EXCLUDED.sentiment,
                        sentiment_score = EXCLUDED.sentiment_score
                """),
                {
                    "id": str(fb_id),
                    "org_id": str(org_id),
                    "prod_id": str(prod[0]),
                    "cust_id": cust_id,
                    "source": source,
                    "rating": rating,
                    "text": text_content,
                    "sentiment": sentiment,
                    "score": score,
                    "themes": json.dumps(themes),
                    "region": "Europe",
                    "fb_date": today - timedelta(days=idx),
                    "created_at": now_dt - timedelta(days=idx),
                },
            )

        session.commit()
        log.info("Upserted 12 customer feedback reviews")

        # ── 6. Executive BI Reports ──────────────────────────────
        log.info("Adding quarterly & weekly executive BI reports...")
        rep_specs = [
            (
                "report-q3-audit",
                "Q3 Operations & Closed-Loop Performance Audit",
                "on_demand",
                3,
                (
                    "## Q3 Comprehensive Performance Audit\n\n"
                    "### Revenue Overview\n"
                    "Total retail turnover reached **£29.4M** across 8,000 completed orders over the rolling evaluation window. "
                    "Gross profit margins held firm at 38.4%, buoyed by high-margin electronics and home goods.\n\n"
                    "### Anomaly & Closed-Loop Resolution\n"
                    "- **Detection Latency**: Anomaly detectors (Z-score + Isolation Forest) identified 10 operational deviations with a median detection time of 1.2 days.\n"
                    "- **Human-in-the-Loop Velocity**: 8 recommended actions generated; 4 approved, 1 rejected, and 3 currently pending managerial sign-off.\n"
                    "- **Value Recovered**: Early intervention prevented an estimated £12,400 in stockout losses and deadstock write-offs.\n\n"
                    "### Inventory Health\n"
                    "- 200 catalog SKUs actively tracked.\n"
                    "- Inventory turnover index: 4.8x.\n"
                    "- Critical stockout alerts declined 35% compared to prior quarter baseline.\n"
                ),
            ),
            (
                "report-weekly-current",
                "Weekly Executive BI Summary & Closed-Loop Action Log",
                "weekly",
                1,
                (
                    "## Weekly Executive Briefing\n\n"
                    "### Current Pulse\n"
                    "Weekly sales volume remained vigorous with **3,120 transactions** booked over the trailing 30 days. "
                    "Demand forecasting models maintained an aggregate test **MAPE of 7.8%**, sustaining accurate replenishment signals.\n\n"
                    "### Priority Action Items\n"
                    "1. **SKU-0001 Reorder**: Approve pending purchase order of 180 units to prevent weekend stockout.\n"
                    "2. **Safety Stock Delta**: Approved safety stock scaling on SKU-0000 (+45 units) is now active in warehouse allocation.\n"
                ),
            ),
        ]

        for rep_key, title, rep_type, days_ago, narrative in rep_specs:
            rep_id = stable_uuid(rep_key)
            agg_data = {
                "report_period": f"Generated {today - timedelta(days=days_ago)}",
                "total_products_monitored": len(prod_rows),
                "total_revenue": 29397604.88,
                "total_orders": 8000,
                "avg_order_value": 3674.70,
            }
            session.execute(
                text("""
                    INSERT INTO reports (id, org_id, generated_by, title, report_type,
                                         aggregated_data, narrative, file_path, created_at)
                    VALUES (:id, :org_id, :gen_by, :title, :rep_type,
                            :agg, :narrative, NULL, :created_at)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        narrative = EXCLUDED.narrative,
                        aggregated_data = EXCLUDED.aggregated_data
                """),
                {
                    "id": str(rep_id),
                    "org_id": str(org_id),
                    "gen_by": str(admin_id),
                    "title": title,
                    "rep_type": rep_type,
                    "agg": json.dumps(agg_data),
                    "narrative": narrative,
                    "created_at": now_dt - timedelta(days=days_ago),
                },
            )

        session.commit()
        log.info("Upserted 2 executive reports")
        log.info("✨ Demo data enrichment complete!")


if __name__ == "__main__":
    enrich_data()
