import pandas as pd
import streamlit as st
import plotly.express as px
from FrontEnd.components import ui

def render_deep_dive_tab(df_sales: pd.DataFrame, stock_df: pd.DataFrame):
    """Exhaustive Advanced Filtering for Deep-Dive Clusters."""
    if df_sales.empty:
        st.info("No data available for deep-dive analysis. Finalized orders (Completed/Shipped) are required.")
        return

    # PRE-PROCESSING: Parsing Product Variants & Local Trends
    # --- Variant Logic (Name-based parsing) ---
    def parse_variants(name):
        parts = str(name).split("-")
        color = parts[1].strip() if len(parts) > 2 else "Unknown"
        size = parts[-1].strip() if len(parts) > 1 else "Unknown"
        return color, size

    if "_variant_parsed" not in df_sales.columns:
        df_sales[["_color", "_size"]] = df_sales["item_name"].apply(lambda x: pd.Series(parse_variants(x)))
        df_sales["_variant_parsed"] = True

    # --- Trend Type Logic ---
    # Calculate velocity based on current window length
    days_active = (df_sales["order_date"].max() - df_sales["order_date"].min()).days or 1
    v_agg = df_sales.groupby("item_name")["qty"].sum().reset_index()
    v_agg["v_rate"] = v_agg["qty"] / days_active
    
    def classify_trend(rate):
        if rate > 3.0: return "🔥 Fast Moving"
        if rate > 0.8: return "⚖️ Regular"
        if rate > 0: return "🐌 Slow Moving"
        return "❄️ Non-Moving"

    v_agg["Trend"] = v_agg["v_rate"].apply(classify_trend)
    if "Trend" not in df_sales.columns:
        df_sales = df_sales.merge(v_agg[["item_name", "Trend"]], on="item_name", how="left")

    # --- Campaign / Coupon logic ---
    if "Coupons" not in df_sales.columns:
        df_sales["Coupons"] = "None"

    # MAIN UI LAYOUT
    st.markdown("### 🔍 Advanced Market Deep-Dive")
    
    # FILTER CONTROL CENTER
    with st.expander("🛠️ Advanced Cluster Filters", expanded=True):
        f_c1, f_c2, f_c3, f_c4 = st.columns(4)
        
        with f_c1:
            st.markdown("**📦 Product & Variants**")
            sel_cats = st.multiselect("Categories", sorted(df_sales["Category"].unique()))
            sel_skus = st.text_input("SKU Search (Exact or Comma-list)")
            sel_colors = st.multiselect("Colors", sorted([c for c in df_sales["_color"].unique() if c != "Unknown"]))
            sel_sizes = st.multiselect("Sizes", sorted([s for s in df_sales["_size"].unique() if s != "Unknown"]))

        with f_c2:
            st.markdown("**💰 Financials**")
            min_p = float(df_sales["price"].min())
            max_p = float(df_sales["price"].max())
            price_range = st.slider("Price Range (TK)", min_p, max_p, (min_p, max_p))
            
            st.markdown("**📉 Moving Trends**")
            sel_trends = st.multiselect("Velocity Type", ["🔥 Fast Moving", "⚖️ Regular", "🐌 Slow Moving"])

        with f_c3:
            st.markdown("**📍 Platform & Geo**")
            sel_sources = st.multiselect("Platform/Source", sorted(df_sales["source"].unique()))
            sel_cities = st.multiselect("Market Regions", sorted(df_sales["city"].unique()))
            
            # Sub-window Filtering (Zoom within range)
            st.markdown("**⏱️ Local Time Frame**")
            start_f, end_f = st.date_input("Zoom Frame", 
                                           [df_sales["order_date"].min().date(), df_sales["order_date"].max().date()],
                                           min_value=df_sales["order_date"].min().date(),
                                           max_value=df_sales["order_date"].max().date())

        with f_c4:
            st.markdown("**🎫 Marketing & Campaigns**")
            coupons = [c for c in df_sales["Coupons"].unique() if c != "None"]
            sel_coupons = st.multiselect("Active Coupons", sorted(coupons))
            
            is_disc = st.checkbox("Show Only Non-Full-Price Orders")
            
            # Logic: Bundle detection (Order has multiple items or specific bundle keywords)
            # Simplification: Multiple qty in one line or specific SKUs
            sel_bundle = st.checkbox("Bundle/Multipack Only")

    # APPLY COMPREHENSIVE FILTERING
    w_df = df_sales.copy()
    
    # Time Zoom
    w_df = w_df[(w_df["order_date"].dt.date >= start_f) & (w_df["order_date"].dt.date <= end_f)]
    
    # Logic Filters
    if sel_cats: w_df = w_df[w_df["Category"].isin(sel_cats)]
    if sel_colors: w_df = w_df[w_df["_color"].isin(sel_colors)]
    if sel_sizes: w_df = w_df[w_df["_size"].isin(sel_sizes)]
    if sel_skus:
        sku_list = [s.strip().lower() for s in sel_skus.split(",") if s.strip()]
        w_df = w_df[w_df["sku"].str.lower().isin(sku_list)]
    
    w_df = w_df[(w_df["price"] >= price_range[0]) & (w_df["price"] <= price_range[1])]
    if sel_trends: w_df = w_df[w_df["Trend"].isin(sel_trends)]
    if sel_sources: w_df = w_df[w_df["source"].isin(sel_sources)]
    if sel_cities: w_df = w_df[w_df["city"].isin(sel_cities)]
    if sel_coupons: w_df = w_df[w_df["Coupons"].isin(sel_coupons)]
    if is_disc: 
        # Check if item_revenue per unit is less than price (price is usually regular_price in WC)
        w_df = w_df[w_df["item_revenue"] < (w_df["price"] * w_df["qty"])]
    if sel_bundle:
        w_df = w_df[w_df["qty"] > 1] # Simple bundle proxy

    # VISUALIZATION SUITE
    st.markdown(f"**Found {len(w_df)} records matching these constraints**")
    
    cluster_t1, cluster_t2, cluster_t3 = st.tabs(["📊 Performance Mix", "🔍 Variant Analysis", "📋 Cluster Data Ledger"])
    
    with cluster_t1:
        c1, c2 = st.columns(2)
        with c1:
            # Trend Revenue Pie
            t_rev = w_df.groupby("Trend")["item_revenue"].sum().reset_index()
            fig = px.pie(t_rev, values="item_revenue", names="Trend", title="Revenue Contribution by Moving Type",
                         hole=0.4, color_discrete_sequence=px.colors.qualitative.Prism)
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            # Source/Platform Bar
            s_rev = w_df.groupby("source")["item_revenue"].sum().reset_index()
            fig = px.bar(s_rev, x="source", y="item_revenue", title="revenue by platform source",
                         color="item_revenue", color_continuous_scale="Tealgrn")
            st.plotly_chart(fig, use_container_width=True)

    with cluster_t2:
        v_c1, v_c2 = st.columns(2)
        with v_c1:
            # Size Distribution
            sz_df = w_df.groupby("_size")["qty"].sum().reset_index()
            fig = px.bar(sz_df, x="_size", y="qty", title="Unit Volume by Size Cluster", 
                         color="qty", color_continuous_scale="Portland")
            st.plotly_chart(fig, use_container_width=True)
        with v_c2:
            # Color Distribution
            clr_df = w_df.groupby("_color")["item_revenue"].sum().reset_index()
            fig = px.pie(clr_df, values="item_revenue", names="_color", title="Revenue by Color Palette",
                         color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig, use_container_width=True)

    with cluster_t3:
        st.dataframe(
            w_df[["order_id", "order_date", "item_name", "sku", "qty", "item_revenue", "Trend", "Coupons", "source", "city"]],
            use_container_width=True, hide_index=True
        )
