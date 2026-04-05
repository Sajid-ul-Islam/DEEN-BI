"""Main retail dashboard powered by the normalized hybrid sales schema."""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from BackEnd.services.customer_insights import generate_customer_insights
from BackEnd.services.hybrid_data_loader import (
    get_data_summary,
    load_comparison_data,
    load_hybrid_data,
    load_live_stream_data,
    load_woocommerce_stock_data,
)
from BackEnd.services.ml_insights import build_ml_insight_bundle
from BackEnd.utils.sales_schema import ensure_sales_schema
from FrontEnd.components.ui_components import (
    render_audit_card,
    render_bi_hero,
    render_commentary_panel,
    render_kpi_note,
    render_section_card,
)
from FrontEnd.utils.error_handler import log_error


def render_dashboard_tab():
    render_bi_hero(
        "Commerce Command Center",
        "A cleaner BI-style operating view for revenue, demand, customer health, and geographic performance. The dashboard is now optimized for WooCommerce-first analysis with less visual noise and clearer executive signals.",
        chips=[
            "WooCommerce-first",
            "Stream sheet locked",
            "Customer intelligence",
            "Modern BI layout",
        ],
    )

    with st.sidebar:
        st.subheader("Data Connectors")
        live_source = st.radio(
            "Executive Trends Source",
            ["WooCommerce API Only", "Merged (Woo + Sheets)", "Historical + Sheets Only"],
            index=0,
            key="dashboard_live_source",
            help="Product, customer, forecast, and inventory views always use WooCommerce API data. This selector only changes the executive trend layer.",
        )

    include_gsheet = live_source in {"Merged (Woo + Sheets)", "Historical + Sheets Only"}
    include_woo = live_source in {"Merged (Woo + Sheets)", "WooCommerce API Only"}

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        start_date = st.date_input("From", value=date(2022, 8, 1), key="dashboard_start_date")
    with col2:
        end_date = st.date_input("To", value=date.today(), key="dashboard_end_date")
    with col3:
        st.markdown("<div style='height: 1.75rem;'></div>", unsafe_allow_html=True)
        load_clicked = st.button("Refresh Data", use_container_width=True, type="primary")

    if load_clicked or "dashboard_data" in st.session_state:
        try:
            # Main Sales DF (can be Merged for Trends/Geo)
            df_sales = ensure_sales_schema(
                load_hybrid_data(
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    include_gsheet=include_gsheet,
                    include_woocommerce=include_woo,
                )
            )
            
            # Restricted DF for Product/Customer Analysis (WooCommerce Only)
            df_woo_only = ensure_sales_schema(
                load_hybrid_data(
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    include_gsheet=False,
                    include_woocommerce=True,
                )
            )
            
            df_customers = generate_customer_insights(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                include_woocommerce=True,
            )
            if df_sales.empty:
                st.warning("No sales data found for the selected date range.")
                return
            st.session_state.dashboard_data = {
                "sales": df_sales,
                "woo_only": df_woo_only,
                "customers": df_customers,
                "summary": get_data_summary(),
                "ml": build_ml_insight_bundle(df_woo_only, df_customers, horizon_days=7),
                "stock": load_woocommerce_stock_data(),
            }
        except Exception as exc:
            log_error(exc, context="Dashboard Load")
            st.error(f"Error loading dashboard data: {exc}")
            return

    if "dashboard_data" not in st.session_state:
        st.info("Select a date range and click Refresh Data to view insights.")
        return

    data = st.session_state.dashboard_data
    df_sales = ensure_sales_schema(data["sales"])
    df_woo_only = ensure_sales_schema(data["woo_only"])
    df_customers = data["customers"]
    summary = data.get("summary", {})
    ml_bundle = data.get("ml", {})
    stock_df = data.get("stock", pd.DataFrame())

    tabs = st.tabs([
        "Executive Summary",
        "Data Audit",
        "Streaming Comparison",
        "Sales Trends",
        "Product Performance",
        "Customer Behavior",
        "Geographic",
        "Inventory",
        "Forecast & Alerts",
    ])
    with tabs[0]:
        render_executive_summary(df_sales, df_customers, summary)
    with tabs[1]:
        render_data_audit(df_sales, df_customers, start_date, end_date)
    with tabs[2]:
        render_live_stream_comparison()
    with tabs[3]:
        render_sales_trends(df_sales)
    with tabs[4]:
        render_product_performance(df_woo_only) # Restricted to WooCommerce
    with tabs[5]:
        render_customer_behavior(df_woo_only, df_customers) # Restricted to WooCommerce
    with tabs[6]:
        render_geographic_insights(df_sales)
    with tabs[7]:
        render_inventory_health(stock_df, ml_bundle.get("forecast", pd.DataFrame()))
    with tabs[8]:
        render_forecast_and_alerts(ml_bundle)


def render_live_stream_comparison():
    st.caption("This comparison is locked to the dedicated Live Stream Google Sheet and the fixed Today vs Last Day comparison sheet.")
    st.subheader("📡 Live Stream Comparison (Today vs Last Day)")
    
    stream_df = load_live_stream_data()
    compare_df = load_comparison_data()
    
    if stream_df.empty:
        st.warning("Live Stream data is currently empty or unavailable.")
        return
        
    s_rev = stream_df["order_total"].sum()
    s_ord = stream_df["order_id"].nunique()
    s_qty = stream_df["qty"].sum()
    
    c_rev = compare_df["order_total"].sum() if not compare_df.empty else 0
    c_ord = compare_df["order_id"].nunique() if not compare_df.empty else 0
    c_qty = compare_df["qty"].sum() if not compare_df.empty else 0
    
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Live Revenue", f"TK {s_rev:,.0f}", _pct_delta(s_rev, c_rev, "vs Last Day"))
    with m2:
        st.metric("Live Orders", f"{s_ord:,}", _pct_delta(float(s_ord), float(c_ord), "vs Last Day"))
    with m3:
        st.metric("Live Units", f"{s_qty:,.0f}", _pct_delta(s_qty, c_qty, "vs Last Day"))
        
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Live Stream Items")
        if not stream_df.empty:
            st.dataframe(stream_df[["order_id", "item_name", "qty", "order_total"]].head(50), use_container_width=True, hide_index=True)
    with c2:
        st.markdown("#### Live Trends")
        if "_imported_at" in stream_df.columns:
            stream_df["_import_time"] = pd.to_datetime(stream_df["_imported_at"], errors="coerce")
            live_trend = stream_df.groupby(stream_df["_import_time"].dt.hour).agg(Revenue=("order_total", "sum")).reset_index()
            fig = px.area(live_trend, x="_import_time", y="Revenue", title="Import Activity (Hour)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Waiting for more stream activity to plot trends.")


def render_inventory_health(stock_df: pd.DataFrame, forecast_df: pd.DataFrame):
    st.subheader("Inventory Health")
    st.caption("Live stock is fetched directly from the WooCommerce REST API.")
    if stock_df is None or stock_df.empty:
        st.info("No live stock snapshot is available yet from WooCommerce.")
        return

    inventory = stock_df.copy()
    inventory["Stock Quantity"] = pd.to_numeric(inventory.get("Stock Quantity", 0), errors="coerce").fillna(0)
    inventory["Price"] = pd.to_numeric(inventory.get("Price", 0), errors="coerce").fillna(0)
    inventory["Inventory Value"] = inventory["Stock Quantity"] * inventory["Price"]

    low_stock_threshold = 5
    low_stock_df = inventory[inventory["Stock Quantity"] <= low_stock_threshold].copy()
    out_of_stock_df = inventory[inventory["Stock Status"].astype(str).str.lower() == "outofstock"].copy()

    notes = [
        f"The inventory snapshot currently covers {len(inventory):,} WooCommerce products.",
        f"{len(low_stock_df):,} products are at or below {low_stock_threshold} units.",
        f"{len(out_of_stock_df):,} products are out of stock right now.",
    ]
    if "_imported_at" in inventory.columns and inventory["_imported_at"].notna().any():
        notes.append(f"Latest stock sync in this session: {inventory['_imported_at'].dropna().max()}.")
    render_commentary_panel("Inventory Commentary", notes)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Products", f"{len(inventory):,}")
        render_kpi_note("Counting mode: WooCommerce product rows")
    with m2:
        st.metric("Low Stock", f"{len(low_stock_df):,}")
        render_kpi_note("Counting mode: stock quantity <= 5")
    with m3:
        st.metric("Out of Stock", f"{len(out_of_stock_df):,}")
        render_kpi_note("Counting mode: stock_status = outofstock")
    with m4:
        st.metric("Inventory Value", f"TK {inventory['Inventory Value'].sum():,.0f}")
        render_kpi_note("Counting mode: stock quantity x price")

    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown("#### Low Stock Watchlist")
        st.dataframe(
            inventory.sort_values(["Stock Quantity", "Name"], ascending=[True, True])
            .head(20)[["Name", "SKU", "Stock Status", "Stock Quantity", "Price", "Inventory Value"]]
            .rename(
                columns={
                    "Name": "Product",
                    "Stock Status": "Status",
                    "Stock Quantity": "Stock Qty",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    with c2:
        status_counts = inventory["Stock Status"].fillna("unknown").astype(str).value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        fig_status = px.bar(
            status_counts,
            x="Status",
            y="Count",
            color="Count",
            title="Stock Status Mix",
            color_continuous_scale="Tealgrn",
        )
        fig_status.update_layout(height=350)
        st.plotly_chart(fig_status, use_container_width=True)

    if forecast_df is not None and not forecast_df.empty and "item_name" in forecast_df.columns:
        demand_view = inventory.merge(
            forecast_df,
            left_on="Name",
            right_on="item_name",
            how="left",
        )
        demand_view["forecast_7d_units"] = pd.to_numeric(demand_view.get("forecast_7d_units", 0), errors="coerce").fillna(0)
        demand_view["suggested_buffer_units"] = pd.to_numeric(demand_view.get("suggested_buffer_units", 0), errors="coerce").fillna(0)
        demand_view["coverage_gap"] = demand_view["Stock Quantity"] - demand_view["suggested_buffer_units"]

        st.markdown("#### Demand vs Stock Coverage")
        st.caption("This compares WooCommerce stock counts against the demand forecast buffer for overlapping product names.")
        st.dataframe(
            demand_view.sort_values(["coverage_gap", "Stock Quantity"], ascending=[True, True])
            .head(20)[
                [
                    "Name",
                    "SKU",
                    "Stock Quantity",
                    "forecast_7d_units",
                    "suggested_buffer_units",
                    "coverage_gap",
                    "risk_level",
                    "reorder_comment",
                ]
            ]
            .rename(
                columns={
                    "Name": "Product",
                    "Stock Quantity": "Stock Qty",
                    "forecast_7d_units": "Forecast 7d",
                    "suggested_buffer_units": "Suggested Buffer",
                    "coverage_gap": "Coverage Gap",
                    "risk_level": "Demand State",
                    "reorder_comment": "Suggestion",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


def render_executive_summary(df_sales: pd.DataFrame, df_customers: pd.DataFrame, summary: dict):
    st.subheader("Executive Summary")
    df = df_sales[df_sales["order_date"].notna()].copy()
    df["order_day"] = df["order_date"].dt.normalize()
    today = pd.Timestamp.now().normalize()
    yesterday = today - pd.Timedelta(days=1)

    today_data = df[df["order_day"] == today]
    yesterday_data = df[df["order_day"] == yesterday]

    total_revenue = float(df["order_total"].sum())
    total_orders = df["order_id"].replace("", pd.NA).dropna().nunique()
    active_customers = df["customer_key"].replace("", pd.NA).dropna().nunique()
    total_items = float(df["qty"].sum())
    pending_count = len(df[df["order_status"].str.lower().isin(["pending", "processing", "on-hold"])])

    today_revenue = float(today_data["order_total"].sum())
    yesterday_revenue = float(yesterday_data["order_total"].sum())
    today_orders = today_data["order_id"].replace("", pd.NA).dropna().nunique()
    yesterday_orders = yesterday_data["order_id"].replace("", pd.NA).dropna().nunique()
    today_aov = today_revenue / today_orders if today_orders else 0
    yesterday_aov = yesterday_revenue / yesterday_orders if yesterday_orders else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Revenue", f"TK {total_revenue:,.0f}", _pct_delta(today_revenue, yesterday_revenue, "today vs yesterday"))
        render_kpi_note("Counting mode: summed line-item revenue")
    with k2:
        st.metric("Orders", f"{total_orders:,}", _pct_delta(today_orders, yesterday_orders, "today vs yesterday"))
        render_kpi_note("Counting mode: distinct normalized order_id")
    with k3:
        overall_aov = total_revenue / total_orders if total_orders else 0
        st.metric("AOV", f"TK {overall_aov:,.0f}", _pct_delta(today_aov, yesterday_aov, "today vs yesterday"))
        render_kpi_note("Counting mode: revenue / distinct orders")
    with k4:
        st.metric("Customers", f"{active_customers:,}")
        render_kpi_note("Counting mode: distinct customer_key")
    with k5:
        st.metric("Pending", f"{pending_count:,}", "Needs action" if pending_count > 5 else "Healthy")
        render_kpi_note("Counting mode: pending, processing, on-hold")

    s1, s2, s3 = st.columns(3)
    with s1:
        st.metric("Items Sold", f"{total_items:,.0f}")
        render_kpi_note("Counting mode: summed qty from visible rows")
        st.caption(f"Historical: {summary.get('historical', 0):,} | Woo: {summary.get('woocommerce_live', 0):,} | Stream: {summary.get('live_stream', 0):,}")
    with s2:
        repeat_rate = 0.0
        if isinstance(df_customers, pd.DataFrame) and not df_customers.empty and "total_orders" in df_customers.columns:
            repeat_rate = float((df_customers["total_orders"] > 1).mean() * 100)
        st.metric("Repeat Rate", f"{repeat_rate:.1f}%")
        render_kpi_note("Counting mode: customers with total_orders > 1")
    with s3:
        latest_date = df["order_date"].max()
        st.metric("Latest Order", latest_date.strftime("%Y-%m-%d %H:%M") if pd.notna(latest_date) else "N/A")
        render_kpi_note("Counting mode: max order_date in filter")

    insights = []
    if pending_count > 10:
        insights.append("Fulfillment pressure is rising. The pending order queue is large enough to justify immediate courier and packing review.")
    mean_basket_qty = df.groupby("order_id")["qty"].sum().mean() if total_orders else 0
    if mean_basket_qty and mean_basket_qty < 1.5:
        insights.append("Basket depth is light. Bundles, cross-sells, and checkout add-ons are the cleanest lever for AOV growth.")
    if isinstance(df_customers, pd.DataFrame) and not df_customers.empty and "segment" in df_customers.columns:
        churned = int((df_customers["segment"] == "Churned").sum())
        if churned:
            insights.append(f"{churned} customers are currently classified as churned. A focused win-back sequence is likely worth testing.")
        vip_count = int((df_customers["segment"] == "VIP").sum())
        if vip_count:
            insights.append(f"{vip_count} customers are in the VIP segment. Protect them with priority support, early launches, and higher-touch campaigns.")
    if not insights:
        insights.append("The core metrics look stable. The biggest next upside will likely come from retention programs and inventory planning.")
    render_commentary_panel("Intelligence Commentary", insights)
    render_data_trust_panel(df_sales)


def render_data_audit(
    df_sales: pd.DataFrame,
    df_customers: pd.DataFrame,
    start_date: date,
    end_date: date,
):
    st.subheader("Data Audit")
    df = ensure_sales_schema(df_sales)
    if df.empty:
        st.info("No rows are available for audit in the current filter.")
        return

    audit_df = df.copy()
    audit_df["order_day"] = audit_df["order_date"].dt.date
    order_counts = (
        audit_df[audit_df["order_id"].replace("", pd.NA).notna()]
        .groupby("order_id")
        .agg(
            first_seen=("order_date", "min"),
            line_items=("order_id", "size"),
            units=("qty", "sum"),
            revenue=("order_total", "sum"),
            sources=("source", lambda s: ", ".join(sorted({str(v) for v in s if str(v).strip()}))),
        )
        .reset_index()
        .sort_values("first_seen", ascending=False)
    )
    per_source = (
        audit_df.groupby("source", dropna=False)
        .agg(
            line_items=("order_id", "size"),
            unique_orders=("order_id", lambda s: s.replace("", pd.NA).dropna().nunique()),
            revenue=("order_total", "sum"),
        )
        .reset_index()
        .rename(columns={"source": "Source"})
        .sort_values(["revenue", "line_items"], ascending=False)
    )
    per_day = (
        audit_df.groupby("order_day", dropna=False)
        .agg(
            line_items=("order_id", "size"),
            unique_orders=("order_id", lambda s: s.replace("", pd.NA).dropna().nunique()),
            customers=("customer_key", lambda s: s.replace("", pd.NA).dropna().nunique()),
            revenue=("order_total", "sum"),
        )
        .reset_index()
        .sort_values("order_day", ascending=False)
    )
    duplicate_orders = (
        order_counts[order_counts["line_items"] > 1][["order_id", "first_seen", "line_items", "units", "revenue", "sources"]]
        .head(25)
    )
    unique_orders = audit_df["order_id"].replace("", pd.NA).dropna().nunique()
    unique_customers = audit_df["customer_key"].replace("", pd.NA).dropna().nunique()
    line_items = len(audit_df)
    min_ts = audit_df["order_date"].min()
    max_ts = audit_df["order_date"].max()

    intro = [
        f"The filter currently requests data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}.",
        f"The loaded dataset contains {line_items:,} visible rows, {unique_orders:,} distinct orders, and {unique_customers:,} distinct customers after normalization.",
    ]
    if pd.notna(min_ts) and pd.notna(max_ts):
        intro.append(
            f"The actual timestamps present in the loaded data run from {min_ts.strftime('%Y-%m-%d %H:%M')} to {max_ts.strftime('%Y-%m-%d %H:%M')}."
        )
    render_commentary_panel("Audit Guidance", intro)

    a1, a2 = st.columns(2)
    with a1:
        render_audit_card(
            "How Order Counting Works",
            "Orders are counted using distinct normalized order_id values. If one checkout contains multiple products, it appears as multiple line items but one order.",
        )
    with a2:
        render_audit_card(
            "How Revenue Counting Works",
            "Revenue is summed from the visible normalized rows in the current filter. That means product-level tables and trend charts use the same filtered dataset shown below.",
        )

    metrics = st.columns(5)
    with metrics[0]:
        st.metric("Line Items", f"{line_items:,}")
        render_kpi_note("Every visible row after normalization")
    with metrics[1]:
        st.metric("Unique Orders", f"{unique_orders:,}")
        render_kpi_note("Distinct order_id values")
    with metrics[2]:
        st.metric("Unique Customers", f"{unique_customers:,}")
        render_kpi_note("Distinct customer_key values")
    with metrics[3]:
        st.metric("Date Coverage", f"{per_day['order_day'].nunique():,}")
        render_kpi_note("Distinct days with at least one row")
    with metrics[4]:
        st.metric("Sources", f"{audit_df['source'].replace('', pd.NA).dropna().nunique():,}")
        render_kpi_note("Distinct active source labels")

    st.markdown("#### Validation Tables")
    c1, c2 = st.columns([1, 1.25])
    with c1:
        st.markdown("##### Source Mix")
        st.dataframe(
            per_source,
            use_container_width=True,
            hide_index=True,
        )
    with c2:
        st.markdown("##### Daily Coverage")
        st.dataframe(
            per_day.rename(
                columns={
                    "order_day": "Date",
                    "line_items": "Line Items",
                    "unique_orders": "Orders",
                    "customers": "Customers",
                    "revenue": "Revenue",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("#### Order-Level Validation Sample")
    st.caption("Use this table to confirm that one order can contain multiple line items while still counting as a single order in KPI cards.")
    st.dataframe(
        order_counts.rename(
            columns={
                "order_id": "Order ID",
                "first_seen": "First Seen",
                "line_items": "Line Items",
                "units": "Units",
                "revenue": "Revenue",
                "sources": "Sources",
            }
        ).head(50),
        use_container_width=True,
        hide_index=True,
    )

    if not duplicate_orders.empty:
        st.markdown("#### Multi-Line Orders")
        st.caption("These are healthy duplicates caused by orders containing more than one item, not double-counted KPI orders.")
        st.dataframe(
            duplicate_orders.rename(
                columns={
                    "order_id": "Order ID",
                    "first_seen": "First Seen",
                    "line_items": "Line Items",
                    "units": "Units",
                    "revenue": "Revenue",
                    "sources": "Sources",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


def render_sales_trends(df: pd.DataFrame):
    st.subheader("Sales Trends")
    df = df[df["order_date"].notna()].copy()
    if df.empty:
        st.info("No date data available for trend analysis.")
        return

    trend_df = df.copy()
    trend_df["order_day"] = trend_df["order_date"].dt.date
    trend_df["day_name"] = trend_df["order_date"].dt.day_name()
    trend_df["day_num"] = trend_df["order_date"].dt.dayofweek
    trend_df["hour"] = trend_df["order_date"].dt.hour

    daily = trend_df.groupby("order_day", as_index=False).agg(Revenue=("order_total", "sum"), Orders=("order_id", "nunique"))
    fig_line = px.line(daily, x="order_day", y="Revenue", title="Daily Revenue", markers=True)
    fig_line.update_layout(height=350, xaxis_title="Date")
    st.plotly_chart(fig_line, use_container_width=True)

    commentary = []
    if not daily.empty:
        peak_day = daily.loc[daily["Revenue"].idxmax()]
        commentary.append(
            f"Peak daily revenue in this selection was TK {peak_day['Revenue']:,.0f} on {peak_day['order_day']}."
        )
        if len(daily) > 1:
            recent_avg = daily["Revenue"].tail(min(7, len(daily))).mean()
            commentary.append(
                f"Recent run-rate is about TK {recent_avg:,.0f} per day based on the latest visible period."
            )
    render_commentary_panel("Trend Commentary", commentary)

    c1, c2 = st.columns(2)
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    by_day = trend_df.groupby("day_name", as_index=False).agg(Orders=("order_id", "nunique"))
    by_day = by_day.set_index("day_name").reindex(day_order, fill_value=0).reset_index()
    by_day.columns = ["Day", "Orders"]
    with c1:
        fig_bar = px.bar(by_day, x="Day", y="Orders", title="Orders by Day of Week", color="Orders", color_continuous_scale="Blues")
        fig_bar.update_layout(height=320)
        st.plotly_chart(fig_bar, use_container_width=True)
    with c2:
        heat = trend_df.groupby(["day_num", "hour"], as_index=False).size()
        heat = heat.rename(columns={"size": "Orders"})
        pivot = heat.pivot(index="day_num", columns="hour", values="Orders").reindex(index=range(7), columns=range(24), fill_value=0)
        fig_heatmap = px.imshow(
            pivot.values,
            x=list(range(24)),
            y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            labels={"x": "Hour", "y": "Day", "color": "Orders"},
            color_continuous_scale="YlOrRd",
            title="Peak Activity Heatmap",
        )
        fig_heatmap.update_layout(height=320)
        st.plotly_chart(fig_heatmap, use_container_width=True)


def render_product_performance(df: pd.DataFrame):
    st.subheader("Product Performance")
    st.caption("This view uses WooCommerce API order items only. Google Sheets are excluded here for cleaner item-level accuracy.")
    if df.empty:
        st.info("No product data available.")
        return

    grouped = df.groupby("item_name").agg(Revenue=("order_total", "sum"), Units=("qty", "sum"), Orders=("order_id", "nunique")).reset_index()
    grouped = grouped[grouped["item_name"].astype(str).str.strip() != ""].sort_values("Revenue", ascending=False)
    if grouped.empty:
        st.info("No product-level metrics are available.")
        return

    top_products = grouped.head(10)
    product_notes = []
    if not top_products.empty:
        leader = top_products.iloc[0]
        product_notes.append(
            f"Top product is {leader['item_name']} with TK {leader['Revenue']:,.0f} revenue and {leader['Units']:,.0f} units sold."
        )
        concentration = top_products["Revenue"].sum() / grouped["Revenue"].sum() if grouped["Revenue"].sum() else 0
        product_notes.append(
            f"The top 10 products contribute {concentration * 100:.1f}% of visible product revenue, which helps show catalog concentration risk."
        )
    render_commentary_panel("Merchandising Commentary", product_notes)

    c1, c2 = st.columns(2)
    with c1:
        fig_top = px.bar(top_products.sort_values("Revenue"), x="Revenue", y="item_name", orientation="h", title="Top Products by Revenue", color="Revenue", color_continuous_scale="Greens")
        fig_top.update_layout(height=400, yaxis_title="Product")
        st.plotly_chart(fig_top, use_container_width=True)
    with c2:
        fig_units = px.bar(top_products.sort_values("Units"), x="Units", y="item_name", orientation="h", title="Top Products by Units Sold", color="Units", color_continuous_scale="Blues")
        fig_units.update_layout(height=400, yaxis_title="Product")
        st.plotly_chart(fig_units, use_container_width=True)

    st.dataframe(top_products.rename(columns={"item_name": "Product"}), use_container_width=True, hide_index=True)


def render_customer_behavior(df_sales: pd.DataFrame, df_customers: pd.DataFrame):
    st.subheader("Customer Behavior")
    st.caption("This view uses WooCommerce API customer and order history only. Google Sheets are excluded here for retention accuracy.")
    if df_customers is None or df_customers.empty:
        st.info("Customer insights are not available yet for the selected period.")
        return

    new_customers = int((df_customers["segment"] == "New").sum()) if "segment" in df_customers.columns else 0
    returning_customers = int((df_customers["total_orders"] > 1).sum()) if "total_orders" in df_customers.columns else 0
    customer_notes = []
    if len(df_customers):
        customer_notes.append(
            f"The customer base in the current filter includes {len(df_customers):,} distinct customers."
        )
    if returning_customers:
        share = (returning_customers / max(len(df_customers), 1)) * 100
        customer_notes.append(
            f"Returning customers account for {share:.1f}% of the visible customer base."
        )
    churned = int((df_customers["segment"] == "Churned").sum()) if "segment" in df_customers.columns else 0
    if churned:
        customer_notes.append(
            f"{churned} customers are flagged as churned, which makes retention automation a high-value next feature."
        )
    render_commentary_panel("Retention Commentary", customer_notes)

    c1, c2 = st.columns(2)
    with c1:
        fig_donut = go.Figure(data=[go.Pie(labels=["New", "Returning"], values=[new_customers, returning_customers], hole=0.45)])
        fig_donut.update_layout(title="New vs Returning Customers", height=320)
        st.plotly_chart(fig_donut, use_container_width=True)
    with c2:
        segment_counts = df_customers["segment"].value_counts().reset_index()
        segment_counts.columns = ["Segment", "Count"]
        fig_segments = px.bar(segment_counts, x="Segment", y="Count", color="Count", title="Customer Segments")
        fig_segments.update_layout(height=320)
        st.plotly_chart(fig_segments, use_container_width=True)

    if all(col in df_customers.columns for col in ["total_orders", "total_revenue"]):
        fig_scatter = px.scatter(
            df_customers,
            x="total_orders",
            y="total_revenue",
            color="segment" if "segment" in df_customers.columns else None,
            size="avg_order_value" if "avg_order_value" in df_customers.columns else None,
            hover_name="primary_name" if "primary_name" in df_customers.columns else None,
            title="Customer Value Matrix",
            labels={"total_orders": "Orders", "total_revenue": "Revenue"},
        )
        fig_scatter.update_layout(height=420)
        st.plotly_chart(fig_scatter, use_container_width=True)


def render_geographic_insights(df: pd.DataFrame):
    st.subheader("Geographic Insights")
    geo = df.copy()
    geo["region"] = geo["state"].where(geo["state"] != "", geo["city"])
    geo = geo[geo["region"].astype(str).str.strip() != ""]
    if geo.empty:
        st.info("No geographic data found in the selected dataset.")
        return

    geo_sales = geo.groupby("region").agg(Revenue=("order_total", "sum"), Orders=("order_id", "nunique")).reset_index().sort_values("Revenue", ascending=False).head(15)
    geo_notes = []
    if not geo_sales.empty:
        leader = geo_sales.iloc[0]
        geo_notes.append(
            f"Top visible region is {leader['region']} with TK {leader['Revenue']:,.0f} revenue from {leader['Orders']:,} orders."
        )
        geo_notes.append(
            "Use this view to prioritize delivery reliability, ad targeting, and stock placement by region."
        )
    render_commentary_panel("Regional Commentary", geo_notes)
    c1, c2 = st.columns(2)
    with c1:
        fig_geo = px.bar(geo_sales.sort_values("Revenue"), x="Revenue", y="region", orientation="h", title="Revenue by Region", color="Revenue", color_continuous_scale="Teal")
        fig_geo.update_layout(height=400, yaxis_title="Region")
        st.plotly_chart(fig_geo, use_container_width=True)
    with c2:
        fig_orders = px.bar(geo_sales.sort_values("Orders"), x="Orders", y="region", orientation="h", title="Orders by Region", color="Orders", color_continuous_scale="Oranges")
        fig_orders.update_layout(height=400, yaxis_title="Region")
        st.plotly_chart(fig_orders, use_container_width=True)


def render_forecast_and_alerts(ml_bundle: dict[str, pd.DataFrame]):
    st.subheader("Forecast & Alerts")
    forecast_df = ml_bundle.get("forecast", pd.DataFrame())
    risk_df = ml_bundle.get("customer_risk", pd.DataFrame())
    anomaly_df = ml_bundle.get("anomalies", pd.DataFrame())

    overview_notes = []
    if not forecast_df.empty:
        lead = forecast_df.iloc[0]
        overview_notes.append(
            f"Highest forecasted item is {lead['item_name']} with about {lead['forecast_7d_units']:.1f} expected units over the next 7 days."
        )
    if not risk_df.empty:
        high_risk = int((risk_df["risk_band"] == "High").sum())
        overview_notes.append(
            f"{high_risk} customers are currently in the high-risk band for churn or inactivity."
        )
    if not anomaly_df.empty:
        overview_notes.append(
            f"{len(anomaly_df):,} recent metric anomalies were detected across revenue, orders, or AOV."
        )
    if not overview_notes:
        overview_notes.append("No predictive signals are available yet. More clean sales history will improve forecast and risk quality.")
    render_commentary_panel("Predictive Commentary", overview_notes)

    top_row = st.columns(3)
    with top_row[0]:
        total_forecast_units = forecast_df["forecast_7d_units"].sum() if not forecast_df.empty else 0
        st.metric("Forecast Units (7d)", f"{total_forecast_units:,.0f}")
    with top_row[1]:
        high_risk = int((risk_df["risk_band"] == "High").sum()) if not risk_df.empty else 0
        st.metric("High-Risk Customers", f"{high_risk:,}")
    with top_row[2]:
        anomaly_count = len(anomaly_df) if not anomaly_df.empty else 0
        st.metric("Anomalies", f"{anomaly_count:,}")

    if not forecast_df.empty:
        c1, c2 = st.columns([1.3, 1])
        with c1:
            fig_forecast = px.bar(
                forecast_df.sort_values("forecast_7d_units"),
                x="forecast_7d_units",
                y="item_name",
                orientation="h",
                color="trend_ratio",
                color_continuous_scale="Tealgrn",
                title="Next 7-Day Demand Forecast",
                labels={"forecast_7d_units": "Forecast Units", "item_name": "Product"},
            )
            fig_forecast.update_layout(height=420)
            st.plotly_chart(fig_forecast, use_container_width=True)
        with c2:
            st.dataframe(
                forecast_df[["item_name", "forecast_7d_units", "suggested_buffer_units", "risk_level", "reorder_comment"]].rename(
                    columns={
                        "item_name": "Product",
                        "forecast_7d_units": "Forecast 7d",
                        "suggested_buffer_units": "Buffer Units",
                        "risk_level": "Demand State",
                        "reorder_comment": "Suggestion",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    if not risk_df.empty:
        st.markdown("#### Customer Risk Recommendations")
        st.dataframe(
            risk_df[["primary_name", "segment", "risk_score", "risk_band", "next_purchase_window_days", "recommended_action"]]
            .head(20)
            .rename(
                columns={
                    "primary_name": "Customer",
                    "segment": "Segment",
                    "risk_score": "Risk Score",
                    "risk_band": "Risk Band",
                    "next_purchase_window_days": "Next Window (days)",
                    "recommended_action": "Recommendation",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    if not anomaly_df.empty:
        st.markdown("#### Metric Anomalies")
        fig_anomaly = px.scatter(
            anomaly_df,
            x="order_day",
            y="z_score",
            color="metric",
            symbol="direction",
            hover_data=["commentary"],
            title="Recent Revenue / Orders / AOV Anomalies",
        )
        fig_anomaly.update_layout(height=360, xaxis_title="Date", yaxis_title="Z-Score")
        st.plotly_chart(fig_anomaly, use_container_width=True)
        st.dataframe(
            anomaly_df[["order_day", "metric", "direction", "z_score", "commentary"]],
            use_container_width=True,
            hide_index=True,
        )


def render_data_trust_panel(df_sales: pd.DataFrame):
    df = ensure_sales_schema(df_sales)
    if df.empty:
        return

    valid_dates = df["order_date"].dropna()
    min_date = valid_dates.min() if not valid_dates.empty else None
    max_date = valid_dates.max() if not valid_dates.empty else None
    unique_orders = df["order_id"].replace("", pd.NA).dropna().nunique()
    unique_customers = df["customer_key"].replace("", pd.NA).dropna().nunique()
    line_items = len(df)
    active_sources = sorted({src for src in df["source"].dropna().astype(str) if src})

    trust_notes = [
        f"Unique orders are counted using distinct `order_id` values after source normalization and deduplication.",
        f"Visible line items in the current filter: {line_items:,}.",
        f"Visible unique orders in the current filter: {unique_orders:,}.",
    ]
    if min_date is not None and max_date is not None:
        trust_notes.append(
            f"Current data window spans from {min_date.strftime('%Y-%m-%d %H:%M')} to {max_date.strftime('%Y-%m-%d %H:%M')}."
        )
    if active_sources:
        trust_notes.append(f"Active sources in this view: {', '.join(active_sources)}.")

    with st.expander("Data Trust Panel", expanded=False):
        render_commentary_panel("How This Dashboard Counts Data", trust_notes)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Line Items", f"{line_items:,}")
            render_kpi_note("Visible normalized rows")
        with c2:
            st.metric("Unique Orders", f"{unique_orders:,}")
            render_kpi_note("Distinct order_id")
        with c3:
            st.metric("Unique Customers", f"{unique_customers:,}")
            render_kpi_note("Distinct customer_key")
        with c4:
            st.metric("Sources", f"{len(active_sources):,}")
            render_kpi_note("Active source labels")

        preview_cols = [col for col in ["order_date", "order_id", "item_name", "qty", "order_total", "source"] if col in df.columns]
        st.caption("Sample rows from the exact filtered dataset used in the KPIs above.")
        st.dataframe(
            df[preview_cols].sort_values("order_date", ascending=False).head(25),
            use_container_width=True,
            hide_index=True,
        )


def _pct_delta(current: float, previous: float, suffix: str = "") -> str | None:
    if previous in (0, None):
        return None
    delta = ((current - previous) / previous) * 100
    return f"{delta:+.1f}% {suffix}".strip()
