# Automation Pivot

Automation Pivot is a Streamlit operations dashboard for DEEN Commerce. It combines live order monitoring, historical sales analysis, customer tracking, logistics workflows, and inventory tools in one workspace.

## What It Does

- `Live Queue`: Uses the `LatestSales` Google Sheet tab as the live operational queue for packing, shipping, and archive review.
- `Sales Analysis`: Uses the local workbook core in `src/data/TotalOrder_TillLastTime.xlsx` and merges only fresh `2026` rows from Google Sheets.
- `Customer Pulse`: Tracks customer growth, retention, CLV, and top customers across the selected date range.
- `Operations`: Includes Pathao processing, parser tools, inventory distribution, WhatsApp export, and WooCommerce helpers.
- `System`: Includes cache health, data completeness, exports, AI tools, and logs.

## Data Model

Historical analysis does not depend on Google Sheets for old years.

- `2022`, `2023`, `2024`, `2025`, and `2026-tillLastTime` are loaded from `src/data/TotalOrder_TillLastTime.xlsx`
- `2026` is checked in Google Sheets for rows that are newer than the workbook snapshot
- `LatestSales` is treated as the live queue for in-process orders
- `2026` is treated as the archive or completed-order ledger

## UI Principles

- Single light theme with consistent contrast across cards, tables, forms, tabs, and alerts
- KPI-first layouts for Live Queue, Sales Analysis, and Customer Pulse
- Reduced noise, fewer redundant panels, and clearer date-range context
- Shared visual pattern across operational and analytical screens

## Project Structure

- `app.py`: App entrypoint and top-level navigation
- `src/core/`: Sync, archive, paths, state, and error handling
- `src/data/`: Normalized sales data helpers and local workbook assets
- `src/services/`: Live queue and master sales services
- `src/modules/`: Sales, logistics, inventory, parser, AI, and system views
- `src/ui/`: Shared components and styling
- `src/utils/`: Generic helpers for data and file I/O

## Local Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Google Sheets Configuration

Set `GSHEET_URL` to the published sheet URL if you are not using the default workbook.

For write access and archive automation, configure:

- `GSHEET_SPREADSHEET_ID` or `GSHEET_EDIT_URL`
- `GSHEET_SERVICE_ACCOUNT_JSON`
- or `GOOGLE_SERVICE_ACCOUNT_EMAIL` and `GOOGLE_PRIVATE_KEY`

## Live Archive Automation

The live dashboard can move finished rows from `LatestSales` into `2026`.

- Add one control column in `LatestSales`: `Archive Status`, `Sync Status`, `Sync to 2026`, or `Archive to 2026`
- Mark rows with one of these values: `ready`, `done`, `completed`, `shipped`, `archive`, `synced`
- Set `AUTO_ARCHIVE_LATESTSALES=true` to run archive automatically on live-page refresh
- `AUTO_ARCHIVE_LASTDAYSALES=true` is still accepted for backward compatibility

## Notes

- Sales Analysis and Customer Pulse now use page-specific date range state
- KPI summaries and charts in those views reflect the selected date range
- Live Queue always reflects the current `LatestSales` tab
