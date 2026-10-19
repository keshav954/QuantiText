# Database Schema — ER Diagram

> Auto-generated from the Phase 1 database design. Updated: 2026-10-15.

## Entity-Relationship Diagram

```mermaid
erDiagram
    orgs ||--o{ users : has
    orgs ||--o{ categories : has
    orgs ||--o{ products : has
    orgs ||--o{ customers : has
    orgs ||--o{ orders : has
    orgs ||--o{ inventory : has
    orgs ||--o{ daily_sales : has
    orgs ||--o{ forecasts : has
    orgs ||--o{ anomalies : has
    orgs ||--o{ alerts : has
    orgs ||--o{ recommendations : has
    orgs ||--o{ reports : has
    orgs ||--o{ audit_log : has

    users {
        uuid id PK
        uuid org_id FK
        string email UK
        string hashed_password
        string full_name
        string role "admin|manager|analyst|viewer"
        bool is_active
        timestamp created_at
        timestamp updated_at
    }

    orgs {
        uuid id PK
        string name
        string slug UK
        text description
        jsonb settings
        timestamp created_at
        timestamp updated_at
    }

    categories {
        uuid id PK
        uuid org_id FK
        string name
        string slug
        timestamp created_at
        timestamp updated_at
    }

    products {
        uuid id PK
        uuid org_id FK
        uuid category_id FK
        string sku
        string name
        string description
        decimal unit_price
        bool is_active
        timestamp created_at
        timestamp updated_at
    }

    customers {
        uuid id PK
        uuid org_id FK
        string customer_code
        string country
        string region
        timestamp created_at
        timestamp updated_at
    }

    orders {
        uuid id PK
        uuid org_id FK
        uuid customer_id FK
        string invoice_no
        timestamp invoice_date
        decimal total_amount
        timestamp created_at
        timestamp updated_at
    }

    order_items {
        uuid id PK
        uuid order_id FK
        uuid product_id FK
        int quantity
        decimal unit_price
        decimal line_total
    }

    inventory {
        uuid id PK
        uuid org_id FK
        uuid product_id FK "unique"
        int stock_on_hand
        int reorder_point
        int lead_time_days
        int min_order_qty
        decimal unit_cost
        decimal holding_cost_pct
        timestamp last_updated
    }

    daily_sales {
        uuid id PK
        uuid org_id FK
        uuid product_id FK
        date sale_date
        int quantity_sold
        decimal revenue
        string region
    }

    forecasts {
        uuid id PK
        uuid org_id FK
        uuid product_id FK
        date forecast_date
        int horizon_days
        decimal predicted_qty
        decimal lower_bound
        decimal upper_bound
        string model_name
        float mape
        timestamp created_at
    }

    anomalies {
        uuid id PK
        uuid org_id FK
        uuid product_id FK
        date detected_date
        string anomaly_type
        string detector "zscore|iforest|data_quality"
        float severity_score
        decimal estimated_impact
        jsonb details
        bool is_dismissed
        timestamp created_at
    }

    alerts {
        uuid id PK
        uuid org_id FK
        uuid anomaly_id FK
        string title
        text description
        string severity "critical|warning|info"
        bool is_read
        timestamp created_at
    }

    recommendations {
        uuid id PK
        uuid org_id FK
        uuid product_id FK
        string action_type "reorder|markdown|investigate"
        text reason
        jsonb parameters
        string status "pending|approved|rejected"
        uuid approved_by FK
        timestamp decided_at
        timestamp created_at
    }

    reports {
        uuid id PK
        uuid org_id FK
        uuid generated_by FK
        string title
        string report_type "weekly|on_demand"
        jsonb aggregated_data
        text narrative
        string file_path
        timestamp created_at
    }

    audit_log {
        uuid id PK
        uuid org_id FK
        uuid user_id FK
        string action
        string resource
        string resource_id
        jsonb details
        string ip_address
        timestamp created_at
    }

    categories ||--o{ products : contains
    products ||--o{ order_items : "sold in"
    products ||--o| inventory : "has stock"
    products ||--o{ daily_sales : "aggregated into"
    products ||--o{ forecasts : "predicted for"
    products ||--o{ anomalies : "detected on"
    products ||--o{ recommendations : "recommended for"
    customers ||--o{ orders : places
    orders ||--|{ order_items : contains
    anomalies ||--o| alerts : triggers
    users ||--o{ audit_log : generates
    users ||--o{ reports : generates
    users ||--o{ recommendations : approves
```

## SQL Views

| View | Purpose | Source Tables |
|------|---------|-------------- |
| `v_kpi_daily` | Daily KPIs: revenue, order count, AOV, unique customers | `orders` |
| `v_sales_by_product` | Product-level totals with category name | `daily_sales`, `products`, `categories` |
| `v_sales_by_region` | Regional breakdown by date | `daily_sales` |
| `v_inventory_status` | Current stock with classification label | `inventory`, `products`, `categories` |

## Access Control

- **`bi_readonly`** role has `SELECT` on views only — used by NL2SQL executor.
- Application queries use the main connection with full access.
- Generated SQL is validated and executed only on the read-only connection.

## Data Notes

> ⚠️ **Inventory, lead-time, and cost data are SYNTHETIC** unless stated otherwise.
> Transactional data comes from the UCI Online Retail II dataset (or synthetic fallback).
