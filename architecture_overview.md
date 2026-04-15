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

- `FrontEnd/components/ui.py` (Central Namespace)
- `FrontEnd/components/layout.py` (Layout & Theme)
- `FrontEnd/components/cards.py` (Visual Sections)
- `FrontEnd/components/charts.py` (Plotly Extensibility)
- `FrontEnd/components/interactive.py` (Dialogs & Menus)
- `FrontEnd/components/metrics.py` (Data Badges)

Responsibilities:

- centralized declarative interface (`from FrontEnd.components import ui`)
- design system styles and Premium BI layout rendering
- hero sections and commentary cards
- audit cards and highlight stats
- component-specific styling logic without bloating a monolith

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

### Customer Insight Module

**Location:** `src/` directory with dedicated submodules

- `src/inheritance/base_api_client.py` - Base HTTP client with retry logic
- `src/services/woocommerce/` - WooCommerce API integration
  - `api_client.py` - WooCommerceAPI class (inherits BaseAPIClient)
  - `fetch_customers.py` - Customer data fetching with caching
  - `fetch_orders.py` - Order data fetching with caching
  - `fetch_products.py` - Product data fetching with caching
- `src/utils/woocommerce_helpers.py` - Data processing utilities
- `src/components/customer_insight/` - UI components
  - `customer_filters.py` - Dynamic filter controls
  - `customer_selector.py` - Customer list and selection
  - `customer_report.py` - Detailed customer reports
  - `order_history_table.py` - Order history display
- `FrontEnd/pages/dashboard_lib/customer_insight_page.py` - Main page controller

**Responsibilities:**

- Live WooCommerce REST API integration
- Dynamic customer filtering by products, amount, orders, date range
- Individual customer deep-dive analysis
- Order history and spending trend visualization
- Real-time data with 1-hour caching
- Error handling with user-friendly messages

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

### Customer Insight flow

1. User configures filters (products, amount range, order count, date range)
2. System fetches orders from `/wp-json/wc/v3/orders` with date filters
3. If product filter active, system also fetches products from `/wp-json/wc/v3/products`
4. Orders are aggregated to customer level using unique phone/email logic
5. Amount and order count filters are applied to aggregated data
6. Matching customers displayed in sortable table with radio selection
7. On selection, system fetches customer details from `/wp-json/wc/v3/customers/{id}`
8. Order history fetched and displayed with metrics calculation
9. Optional spending trend chart generated from order totals
10. All data cached with 1-hour TTL; manual refresh available

**API Endpoints Used:**
- `GET /wp-json/wc/v3/customers` - List customers with pagination
- `GET /wp-json/wc/v3/customers/{id}` - Individual customer details
- `GET /wp-json/wc/v3/orders` - List orders with filters
- `GET /wp-json/wc/v3/products` - List products for filtering

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
- put reusable display logic in `FrontEnd/components/` specific themed files, accessible via the `ui` module
- put cache, loading, sync, and analytical logic in `BackEnd/services/`
- reuse the page registry rather than wiring tabs directly in `app.py`
- prefer extending canonical schema logic before adding page-local column hacks

## 7. Technical Debt

Legacy unused `.py` scripts and monolith UI references have been cleanly purged to maintain optimal navigation efficiency in the workspace. All features operate explicitly through the `FrontEnd.pages` core loop.
