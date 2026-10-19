# Architecture Diagram

## System Overview

```mermaid
graph TB
    subgraph Client
        UI["React + Vite Frontend"]
    end

    subgraph "Reverse Proxy"
        NGINX["NGINX<br/>Rate Limits + Security Headers"]
    end

    subgraph "Backend (FastAPI)"
        API["API Layer<br/>9 Routers"]
        SVC["Service Layer"]
        LLM["LLM Provider<br/>Gemini / Ollama"]

        API --> SVC
        SVC --> LLM
    end

    subgraph "Data Layer"
        PG["PostgreSQL 16"]
        RD["Redis 7"]
    end

    subgraph "ML Pipeline"
        ML["Forecasting<br/>Prophet + LightGBM"]
        AD["Anomaly Detection<br/>Z-score + IForest"]
    end

    UI --> NGINX
    NGINX --> API
    SVC --> PG
    SVC --> RD
    SVC --> ML
    SVC --> AD
```

## Request Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant N as NGINX
    participant A as FastAPI
    participant S as Service
    participant D as PostgreSQL
    participant L as LLM

    U->>F: Interact with UI
    F->>N: HTTP Request + JWT
    N->>A: Proxy (rate limited)
    A->>A: Auth + RBAC check
    A->>S: Business logic
    S->>D: Query data
    D-->>S: Results
    S->>L: Generate narrative/SQL
    L-->>S: LLM response
    S-->>A: Formatted response
    A-->>N: JSON
    N-->>F: Response
    F-->>U: Render UI
```

## Closed-Loop Pipeline

```mermaid
graph LR
    A["Anomaly<br/>Detected"] --> B["Root Cause<br/>Analysis"]
    B --> C["Forecast<br/>Impact"]
    C --> D["Recommendation<br/>Generated"]
    D --> E["Human<br/>Approval"]
    E --> F["Action<br/>Logged"]
    F --> G["Outcome<br/>Tracked"]
    G -.-> A
```

## Data Model (Key Tables)

```mermaid
erDiagram
    orgs ||--o{ users : has
    orgs ||--o{ products : owns
    orgs ||--o{ orders : receives
    orgs ||--o{ reports : generates

    products ||--o{ order_items : sold_in
    products ||--o{ daily_sales : tracked
    products ||--o{ inventory : stocked
    products ||--o{ forecasts : predicted
    products ||--o{ anomalies : monitored
    products ||--o{ recommendations : targeted

    orders ||--o{ order_items : contains

    users ||--o{ chat_sessions : creates
    users ||--o{ reports : generates
    users ||--o{ recommendations : approves
```

## Module Map

| Module | Router | Service | Models |
|--------|--------|---------|--------|
| Auth & RBAC | `auth.py` | `auth_service.py` | `user.py`, `org.py` |
| KPI Dashboard | `kpi.py` | `kpi_service.py` | views: `v_kpi_daily` |
| Forecasting | `forecast.py` | `forecasting_service.py` | `analytics.py` |
| Inventory | `inventory.py` | `inventory_service.py` | `inventory.py` |
| Anomaly Detection | `anomaly.py` | `anomaly_service.py` | `alert.py` |
| AI Copilot (NL2SQL) | `copilot.py` | `copilot_service.py` | `chat_session.py` |
| Reports & Approvals | `report.py` | `report_service.py` | `report.py` |
| BYOD Upload | `admin.py` | `upload_service.py` | — |
| LLM Abstraction | — | `llm/` | — |
