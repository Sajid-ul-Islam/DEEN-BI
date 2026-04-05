# DEEN Commerce BI

DEEN Commerce BI is a WooCommerce-first Streamlit business intelligence workspace for e-commerce sales, customer intelligence, inventory visibility, and operational diagnostics.

The current app is organized around four primary workspaces:

- `Business Intelligence`: executive KPIs, sales analysis, customer behavior, inventory, forecasts, and data-audit views
- `Customer Intelligence`: lifetime customer metrics, RFM segmentation, and retention context
- `Commerce Hub`: WooCommerce order sync, inventory fetch, previews, and local storage utilities
- `System Health`: logs, diagnostics, and operational trust tools

## Product Direction

This codebase now follows a few key principles:

- WooCommerce is the primary operational source for orders, customers, and inventory
- local cache is treated as a first-class runtime layer for speed
- long-running refresh work happens in the background whenever possible
- the dashboard defaults to the latest 30 days of WooCommerce activity for a lighter load
- historical WooCommerce data is loaded only on demand when deeper retention context is needed
- UI components and date handling are shared across pages for a more homogeneous product feel

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Default Loading Behavior

The app now uses lighter defaults for the main BI workflow:

- `Business Intelligence` opens with the latest 30 days of WooCommerce sales data
- the default sync action refreshes only that rolling 30-day sales window plus inventory cache
- full WooCommerce history is not loaded automatically on dashboard open
- historical customer context is available through an explicit `Load Historical Data` action

## Core Architecture

### Frontend

- [app.py](H:/Analysis/Automation-Pivot/app.py): thin application shell, sidebar controls, page registry rendering
- [FrontEnd/pages/__init__.py](H:/Analysis/Automation-Pivot/FrontEnd/pages/__init__.py): primary page registry and page metadata
- [FrontEnd/components/ui_components.py](H:/Analysis/Automation-Pivot/FrontEnd/components/ui_components.py): shared design system, highlight cards, commentary blocks, and loaded-date context helpers

### Backend

- [BackEnd/services/hybrid_data_loader.py](H:/Analysis/Automation-Pivot/BackEnd/services/hybrid_data_loader.py): WooCommerce-focused loading, local cache management, background refresh jobs, full-history sync status
- [BackEnd/services/woocommerce_service.py](H:/Analysis/Automation-Pivot/BackEnd/services/woocommerce_service.py): WooCommerce API access for orders and stock
- [BackEnd/services/customer_insights.py](H:/Analysis/Automation-Pivot/BackEnd/services/customer_insights.py): customer normalization, lifetime metrics, RFM segmentation, and first-order logic
- [BackEnd/services/ml_insights.py](H:/Analysis/Automation-Pivot/BackEnd/services/ml_insights.py): demand forecast, churn-risk scoring, anomaly detection
- [BackEnd/utils/sales_schema.py](H:/Analysis/Automation-Pivot/BackEnd/utils/sales_schema.py): canonical sales schema normalization

## Data Strategy

The app uses a WooCommerce local-first strategy:

1. WooCommerce order and stock cache is read first for fast UI response
2. stale or missing WooCommerce cache is refreshed in the background
3. lifetime WooCommerce history can be built through a one-time on-demand full sync
4. cached sales data is reused locally per user to keep the UI fast

## Customer and Revenue Counting

### Revenue

- dashboard and BI revenue uses one `order_total` per distinct `order_id`
- this avoids double-counting multi-item orders in flattened line-item datasets
- product analysis uses estimated line revenue instead of repeated full-order totals

### Customers

- `Unique Customers` means distinct normalized customers inside the visible filter
- `New Customers` means customers whose first-ever WooCommerce order falls inside the relevant period
- default dashboard customer views reflect the rolling 30-day window
- lifetime customer metrics become more accurate after an on-demand historical WooCommerce sync

## Working with the Codebase

Recommended areas for future work:

- add more small helpers in `FrontEnd/components/ui_components.py` before duplicating UI markup in pages
- keep page-specific rendering in `FrontEnd/pages/`
- keep data retrieval, cache management, and model logic in `BackEnd/services/`
- keep schema normalization and WooCommerce field cleanup in `BackEnd/utils/`
- prefer extending the page registry in `FrontEnd/pages/__init__.py` instead of wiring page tabs directly in `app.py`

## Legacy / Archived Areas

Some older modules still exist in the repository for backward reference or recovery work, including AI assistant and older operational tools. They are not part of the current primary navigation and should be treated as secondary unless explicitly reintroduced.

## Verification

Typical local verification commands:

```bash
python -m py_compile app.py FrontEnd\pages\dashboard.py FrontEnd\pages\customer_insights.py FrontEnd\pages\woocommerce.py
python -m unittest tests.test_hybrid_data_loader tests.test_customer_history tests.test_dashboard_revenue
```
