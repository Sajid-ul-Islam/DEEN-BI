"""Optimized Main Dashboard Controller using a modular library structure."""

from __future__ import annotations
from datetime import date, timedelta, datetime
import pandas as pd
import streamlit as st

from BackEnd.services.customer_insights import generate_customer_insights_from_sales
from BackEnd.services.hybrid_data_loader import (
    get_woocommerce_orders_cache_status,
    load_hybrid_data,
    load_cached_woocommerce_stock_data,
    start_orders_background_refresh,
)
from BackEnd.services.ml_insights import build_ml_insight_bundle
from FrontEnd.components import ui
from FrontEnd.utils.error_handler import log_error

# Modular Library Imports
from .dashboard_lib.data_helpers import prune_dataframe, build_order_level_dataset, sum_order_level_revenue
from .dashboard_lib.story import render_dashboard_story
from .dashboard_lib.metrics import render_executive_summary
from .dashboard_lib.bi_analytics import (
    render_today_vs_last_day_sales_chart,
    render_last_7_days_sales_chart
)
from .dashboard_lib.trends import render_sales_trends
from .dashboard_lib.performance import render_product_performance
from .dashboard_lib.inventory import render_inventory_health
from .dashboard_lib.audit import render_data_audit, render_data_trust_panel

DASHBOARD_SALES_COLUMNS = [
    "order_id", "order_date", "order_total", "customer_key", "customer_name",
    "order_status", "source", "city", "state", "qty", "item_name",
    "item_revenue", "line_total", "item_cost", "price"
]

from .customer_insights import render_customer_insight_tab
from .orders_analytics import render_orders_analytics_tab

def render_intelligence_hub_page():
    st.markdown('<div class="live-indicator"><span class="live-dot"></span>System Online | Intelligence Hub Active</div>', unsafe_allow_html=True)
    
    ui.hero(
        "Vision Hub",
        "Unified business intelligence: Executive KPIs, Customer Behavior, and Cluster-based Sales Analytics.",
        chips=[f"Last Sync: {datetime.now().strftime('%H:%M')}", "v2.5.0", "Material Design"]
    )
    
    global_sync = st.session_state.get("global_sync_request", False)
    if global_sync:
        st.session_state["global_sync_request"] = False # Reset
        
    # 1. Map Time Window to Query Range
    window = st.session_state.get("time_window", "Last 7 Days")
    window_map = {
        "Last Day": 1,
        "Last 7 Days": 7,
        "Last Month": 30,
        "Last Quarter": 90,
        "Last Year": 365
    }
    days_back = window_map.get(window, 7)
    
    end_date_str = date.today().strftime("%Y-%m-%d")
    start_date_str = (date.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    orders_status = get_woocommerce_orders_cache_status(start_date_str, end_date_str)
    start_orders_background_refresh(start_date_str, end_date_str, force=global_sync)
    
    # Store dynamic range in session to detect window change
    if global_sync or "dashboard_data" not in st.session_state or st.session_state.get("last_window") != window:
        with st.spinner(f"Synchronizing Intelligence Hub ({window})..."):
            st.session_state["last_window"] = window
            df_sales = prune_dataframe(load_hybrid_data(start_date=start_date_str, end_date=end_date_str, woocommerce_mode="cache_only"), DASHBOARD_SALES_COLUMNS)
            df_customers = generate_customer_insights_from_sales(df_sales, include_rfm=True)
            ml_bundle = build_ml_insight_bundle(df_sales, df_customers, horizon_days=7)
            stock_df = load_cached_woocommerce_stock_data()
            
            st.session_state.dashboard_data = {
                "sales": df_sales,
                "customers": df_customers,
                "ml": ml_bundle,
                "stock": stock_df,
                "summary": {"woocommerce_live": len(df_sales), "stock_rows": len(stock_df)},
                "hint": orders_status.get("status_message", "")
            }

    data = st.session_state.dashboard_data
    
    # 1. Core Metrics (6 Pillars)
    df_exec = data["sales"][data["sales"]["order_date"].notna()].copy()
    exec_orders = build_order_level_dataset(df_exec)
    
    total_rev = sum_order_level_revenue(df_exec)
    order_count = exec_orders["order_id"].nunique() if not exec_orders.empty else 0
    cust_count = df_exec["customer_key"].nunique()
    total_items = df_exec["qty"].sum()
    
    aov = (total_rev / order_count) if order_count else 0
    basket_value = (total_rev / total_items) if total_items else 0
    
    # 2-Row Metric Layout
    m1, m2, m3 = st.columns(3)
    with m1: ui.icon_metric("Total Item Sold", f"{total_items:,}", icon="📦")
    with m2: ui.icon_metric("Revenue", f"৳{total_rev:,.0f}", icon="💰")
    with m3: ui.icon_metric("Orders", f"{order_count:,}", icon="🛒")
    
    m4, m5, m6 = st.columns(3)
    with m4: ui.icon_metric("Basket Value", f"৳{basket_value:,.0f}", icon="🧺")
    with m5: ui.icon_metric("Customers", f"{cust_count:,}", icon="👥")
    with m6: ui.icon_metric("Avg. Order", f"৳{aov:,.0f}", icon="💎")

    st.markdown("<br>", unsafe_allow_html=True)

    # Routing based on sidebar selection
    selection = st.session_state.get("active_section", "💎 Executive Dashboard")

    if selection == "💎 Executive Dashboard":
        render_dashboard_story(data["sales"], data["customers"], data["ml"])
        render_executive_summary(data["sales"], data["customers"], data["summary"])
    
    elif selection == "👥 Customer Behavior":
        st.subheader("Customer Intelligence")
        render_customer_insight_tab()
        
    elif selection == "🔍 Deep-Dive Clusters":
        st.subheader("Cluster-based Analytics")
        render_orders_analytics_tab()
        
    elif selection == "📦 Inventory Health":
        st.subheader("Operational Health")
        render_inventory_health(data["stock"], data["ml"].get("forecast"))
        
    elif selection == "🛡️ Data Trust":
        st.subheader("System Integrity")
        render_data_trust_panel(data["sales"])
        render_data_audit(data["sales"], data["customers"])
