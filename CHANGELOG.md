# DEEN Commerce BI Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.6.0] - 2026-04-05

### Changed
- Renamed the active app branding to `DEEN Commerce BI`
- Changed the Business Intelligence dashboard to load the latest 30 days of WooCommerce data by default
- Moved historical WooCommerce loading behind an explicit on-demand action instead of automatic dashboard startup sync
- Reorganized the app around a registry-driven primary navigation model
- Simplified `app.py` into a thinner shell with sidebar helpers and dynamic page rendering
- Standardized date defaults across the app to `2022-08-01` through `today`
- Unified loaded-date context messaging across dashboard, customer, and WooCommerce pages
- Improved component exports so shared UI helpers are easier to reuse consistently

### Added
- `PRIMARY_PAGE_CONFIG` in `FrontEnd/utils/config.py` for page metadata and future navigation changes
- `PrimaryPage` registry in `FrontEnd/pages/__init__.py`
- shared highlight-stat and loaded-date-context UI helpers
- workspace view descriptions in the sidebar for faster onboarding

### Fixed
- Brought the README and architecture documentation in line with the current WooCommerce-first BI application structure
- Removed several readability issues caused by direct page wiring and repeated navigation knowledge

## [2.5.0] - 2026-04-03

### Fixed
- Resolved Git merge conflicts in `components.py` that caused broken UI rendering
- Removed duplicate `render_wp_tab` import in `app.py`
- Fixed undefined variables (`sm`, `deltas`, `cust_metrics`) in `sales.py` `render_story_summary()` function
- Created missing `normalized_sales.py` module with data normalization and analytics functions
- Fixed syntax errors in `render_sidebar_workspace_control()` function

### Added
- **Mobile Responsive Styles**: Added `@media` breakpoints for mobile devices (max-width: 768px)
- **Accessibility Improvements**: Added `focus-visible` styles for keyboard navigation
- **CHANGELOG**: Added this changelog file with semantic versioning
- **Pre-commit Hooks**: Added `.pre-commit-config.yaml` for code quality enforcement
- **Data Normalization Module**: Created `src/data/normalized_sales.py` with:
  - Canonical column mapping for sales data
  - Column alias detection from various source formats
  - Sales analytics computation (summary, basket, trends, customers)
  - Period-over-period comparison functions
  - Customer counting utilities

### Changed
- Consolidated CSS styles from both merge branches
- Improved `render_date_range_selector()` with better state management
- Updated footer to use `APP_VERSION` from config

### Security
- No security changes in this release

## [2.4.0] - 2026-03-24

### Added
- Live Queue dashboard with auto-refresh capability
- Google Sheets archive automation for completed orders
- WooCommerce API integration for order fetching
- Customer Pulse analytics with retention metrics
- Operations hub with Pathao, Parser, Inventory, WhatsApp, and WooCommerce tabs
- AI Analyst chat interface
- Data completeness and quality monitoring

### Changed
- Migrated historical data from Google Sheets to local Excel workbook
- Updated data model to use `TotalOrder_TillLastTime.xlsx` for 2022-2025 data
- Added 2026 delta sync from Google Sheets

## [2.3.0] - 2026-02-15

### Added
- Period-over-period (PoP) comparative analytics
- Automated insights generation for sales analysis
- Export functionality for analysis workbooks
- Cache health monitoring panel

### Fixed
- Improved Google Sheets sync reliability
- Fixed column mapping for various data sources

## [2.2.0] - 2026-01-20

### Added
- Inventory distribution tools
- Fuzzy parser for order data
- WhatsApp export functionality
- System logs and error tracking

### Changed
- Refactored UI components for consistency
- Improved caching strategy with intelligent TTL

## [2.1.0] - 2025-12-10

### Added
- Pathao logistics integration
- Category-based sales analysis
- KPI dashboard with delta indicators

## [2.0.0] - 2025-11-01

### Added
- Initial release of DEEN Commerce BI
- Streamlit-based operations dashboard
- Google Sheets integration for live order tracking
- Sales analysis with Plotly charts
- Customer tracking and CLV metrics
- Excel export functionality

### Changed
- Complete rewrite from legacy system
- New UI design system with CSS variables

---

## Version Format

Version numbers follow `MAJOR.MINOR.PATCH`:

- **MAJOR**: Incompatible API changes or major feature releases
- **MINOR**: New functionality (backward compatible)
- **PATCH**: Bug fixes (backward compatible)
