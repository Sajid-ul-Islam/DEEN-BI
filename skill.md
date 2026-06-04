# DEEN-BI System Capabilities & Skills

This document outlines the core functional "skills" of the DEEN-BI platform, categorized by business domain.

## 1. Sales & Revenue Intelligence
- **High-Fidelity Time-Series Analysis**: Tracking daily revenue, order volume, and unit sales with support for period-over-period comparisons (Today vs. Yesterday, WoW, MoM).
- **AOV & Basket Depth Tracking**: Calculating Average Order Value trends and monitoring items per order to identify cross-sell opportunities.
- **Net Sales Calculation**: Logic to derive true "Settled Sales" by subtracting return losses and partial refund impacts from gross revenue.

## 2. Returns & Operational Recovery
- **Return Classification**: Categorizing delivery issues into Paid Returns, Non-Paid Returns, Partials, and Exchanges.
- **Financial Impact Attribution**: Semantically matching returned items back to WooCommerce orders to calculate precise revenue extraction and loss.
- **Customer Recovery Tracking**: Identifying "Loyal Returners"—customers who reorder despite having experienced a return or exchange.
- **Return Reason Analysis**: Pattern matching of customer/courier feedback to predict and prevent future returns (e.g., size charts for high size-issue categories).
- **Outlet Dispatch Intelligence**: Analyzing returns, partials, and exchanges segmented by dispatch location (Ecom, Wari, Cumilla, Sylhet) via order ID heuristics.

## 3. Inventory & Supply Chain Strategy
- **Velocity-Based Forecasting**: Classifying SKUs by movement (Hot, Stable, Slow, Dead) to generate strategic restock alerts.
- **Orphan Stock Detection**: Identifying stranded inventory where a high-affinity paired item is out of stock, preventing lost bundle sales.
- **Historical Stock Snapshots**: Reconstructing inventory levels for any past date by back-calculating from current stock via sales and return logs.
- **Sub-Category P&L**: Detailed reporting on unit-level profitability, including net yield after returns for specific product clusters.

## 4. Customer Behavior & Loyalty
- **RFM Segmentation**: Automated clustering of customers into VIP, At Risk, Churned, and New segments based on Recency, Frequency, and Monetary value.
- **Loyalty Tiering**: Dynamic scoring (Platinum, Gold, Silver) based on spending history and order consistency.
- **Cohort Retention Analysis**: Matrix visualization of customer and revenue retention over subsequent months from the first purchase.
- **Consolidated Identity Mapping**: Merging WooCommerce registered accounts with guest shopper data and external ledger sheets for a unified customer view.

## 5. Predictive Analytics & AI
- **AutoML Ensemble Forecasting**: Using a tournament of models (ARIMA, SARIMA, Prophet, Holt-Winters) to predict the next 7 days of revenue and orders.
- **Proactive Anomaly Detection**: Real-time monitoring for unusual spikes in refund rates, shipping latency, or sudden drops in conversion.
- **RAG-Powered Data Pilot**: A semantic "Data Pilot" assistant that can query the live database using natural language, generate Plotly charts, and remember custom business rules.
- **Strategy Simulation**: "What-If" modeling to project the financial impact of reducing return rates or increasing conversion.

## 6. Forecasting Model Zoo (AutoML Engine)
- **Croston’s Method (SBA Variant)**: Specifically optimized for intermittent demand patterns, preventing over-forecasting of low-velocity or sparse SKUs.
- **Holt-Winters Exponential Smoothing**: Captures complex triple seasonality (level, trend, and seasonal components) for steady-growth categories.
- **SARIMAX**: A statistical powerhouse used for non-stationary data that accounts for external factors and seasonal cycles.
- **Ridge & LASSO Regression**: Feature-engineered models that utilize high-dimensional rolling lags to detect short-term momentum.
- **XGBoost & LightGBM**: Gradient-boosted decision trees that identify non-linear relationships and complex interactions between product categories.
- **Prophet (Additive Model)**: Robustly handles outliers, large shifts in growth, and Bangladesh-specific holiday effects.
- **Naive & Drift Baselines**: Constant benchmark monitoring to ensure ML models are consistently outperforming simple statistical averages.

## 7. Geographic & Market Intelligence
- **Regional Density Mapping**: Choropleth visualization of Bangladesh’s 64 districts to identify high-revenue zones and logistics bottlenecks.
- **Neighborhood Hotspot Analysis**: Refining delivery data to isolate specific high-performing areas within major cities.

## 8. Technical Operations
- **Staged UI Loading**: Utilizing skeleton components and background threading to ensure the dashboard remains interactive while heavy data syncs occur.
- **Hybrid Data Orchestration**: A multi-tier caching system (Memory -> Parquet -> API) that minimizes WooCommerce server load while maintaining data freshness.
- **Automated BI Reporting**: Multi-sheet Excel generator that injects ML forecasts and AI-generated executive summaries into standard exports.

---
*Last Updated: May 2026*