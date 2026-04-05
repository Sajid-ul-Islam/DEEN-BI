# DEEN Commerce BI Architecture

This document describes the current application architecture for DEEN Commerce BI after the WooCommerce-first BI refactor.

## 1. Application Shape

DEEN Commerce BI is structured as a local-first analytics app with a thin Streamlit shell and a service-oriented backend.

### Primary navigation

- `Business Intelligence`
- `Customer Intelligence`
- `Commerce Hub`
- `System Health`

These primary workspaces are registered centrally in:

- `FrontEnd/utils/config.py`
- `FrontEnd/pages/__init__.py`

That registry-based approach keeps `app.py` small and makes future navigation changes predictable.

## 2. Frontend Layers

### App shell

- `app.py`

Responsibilities:

- page config
- numbered dataframes
- sidebar controls
- page registry rendering
- bootstrap-level error handling

### Pages

- `FrontEnd/pages/dashboard.py`
- `FrontEnd/pages/customer_insights.py`
- `FrontEnd/pages/woocommerce.py`
- `FrontEnd/pages/system_health.py`

Responsibilities:

- page-specific user flow
- feature composition
- page-level charts, commentary, and previews

### Shared components

- `FrontEnd/components/ui_components.py`

Responsibilities:

- design system styles
- hero sections
- commentary cards
- audit cards
- highlight stats
- loaded-date context display
- export helpers

## 3. Backend Layers

### Core services

- `BackEnd/services/hybrid_data_loader.py`
- `BackEnd/services/woocommerce_service.py`
- `BackEnd/services/customer_insights.py`
- `BackEnd/services/ml_insights.py`

Responsibilities:

- WooCommerce sales dataset loading
- WooCommerce API access
- local cache persistence
- background refresh scheduling
- on-demand full WooCommerce history sync
- customer-lifecycle metrics
- forecasting and anomaly signals

### Utilities

- `BackEnd/utils/sales_schema.py`

Responsibilities:

- canonical column mapping
- normalized identifiers
- schema cleanup across WooCommerce order and inventory exports

## 4. Data Flow

### Sales and customer flow

1. load WooCommerce cache if available
2. show cache-backed UI immediately
3. trigger background refresh if stale or incomplete
4. recompute customer and BI views from normalized data
5. use the latest 30 days by default for dashboard rendering
6. load lifetime WooCommerce history only when the user explicitly requests it for deeper retention logic

### Inventory flow

1. fetch stock from WooCommerce REST API
2. cache local stock snapshot
3. reuse cached inventory while refresh runs
4. compare stock against demand forecast

## 5. Trust and Consistency Rules

The current app emphasizes user trust through a few shared rules:

- the main BI dashboard defaults to the latest 30 days of WooCommerce activity
- pages show requested date range and actual loaded activity range
- revenue in BI and KPI views is counted once per order
- unique customers are filter-based
- new customers are based on the best available history in local cache
- WooCommerce history sync is on-demand and does not block the UI

## 6. Future Development Guidance

When adding features:

- put UI composition in `FrontEnd/pages/`
- put reusable display logic in `FrontEnd/components/ui_components.py`
- put cache, loading, sync, and analytical logic in `BackEnd/services/`
- reuse the page registry rather than wiring tabs directly in `app.py`
- prefer extending canonical schema logic before adding page-local column hacks

## 7. Legacy Code

The repository still contains older modules and historical structures under `src/` and some non-primary frontend pages. These remain useful as reference material, but the active product path is the registry-driven Streamlit app described above.
