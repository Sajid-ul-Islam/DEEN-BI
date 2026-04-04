import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from src.core.data_engine import load_and_merge_data, get_customer_insights

def mask_email(email):
    """Mask email for privacy, e.g., j***@gmail.com."""
    if pd.isna(email) or not isinstance(email, str) or '@' not in email:
        return email
    user, domain = email.split('@')
    return f"{user[0]}***@{domain}"

def render_retail_dashboard():
    """Renders the professional E-commerce Retail Sales Dashboard."""
    st.header("🛒 Executive Retail Hub")
    
    # 1. Sidebar - Filters & Refresh
    with st.sidebar:
        st.subheader("🛠️ Dashboard Control")
        if st.button("🔄 Force Refresh (Clear Cache)"):
            st.cache_data.clear()
            st.rerun()
            
        # Select Date Range
        try:
            default_start = datetime.now() - timedelta(days=365)
            default_end = datetime.now()
            d_range = st.date_input("Date Range Filter", value=(default_start, default_end))
        except:
            d_range = (None, None)

    # 2. Fetch Data
    with st.spinner("DuckDB is merging records..."):
        df_all = load_and_merge_data()
        df_customers = get_customer_insights(df_all)
    
    if df_all.empty:
        st.warning("No data found to display. Please check live connection/local fallback.")
        return

    # 3. Filter Data
    if len(d_range) == 2:
        start_date, end_date = d_range
        # Filter df_all by Date Range
        df_all = df_all[(df_all['Order Date'].dt.date >= start_date) & 
                        (df_all['Order Date'].dt.date <= end_date)]
        
    # Segment Multiselect in Sidebar after data is loaded
    with st.sidebar:
        all_segments = ["VIP", "At Risk", "New", "Churned", "Active"]
        selected_segments = st.multiselect("Customer Segment", all_segments, default=all_segments)
        
    # Filter Customers by Segment
    if df_customers is not None and not df_customers.empty:
        df_customers = df_customers[df_customers['Segment'].isin(selected_segments)]
        
    # 4. Executive Summary Row (st.metric)
    total_revenue = df_all['Revenue'].sum()
    total_orders = len(df_all)
    aov = total_revenue / total_orders if total_orders > 0 else 0
    active_customers = df_customers['Customer_ID'].nunique() if not df_customers.empty else 0
    
    # Simple delta calculation Today vs Yesterday for Revenue/Orders (if current data is available)
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    rev_today = df_all[df_all['Order Date'].dt.date == today]['Revenue'].sum()
    rev_yesterday = df_all[df_all['Order Date'].dt.date == yesterday]['Revenue'].sum()
    delta_revenue = f"{(rev_today - rev_yesterday):,.2f}" if rev_yesterday > 0 else None
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Revenue", f"TK {total_revenue:,.2f}", delta=f"TK {delta_revenue}" if delta_revenue else None)
    m2.metric("Total Orders", f"{total_orders:,.0f}")
    m3.metric("Avg Order Value", f"TK {aov:,.2f}")
    m4.metric("Active Customers", f"{active_customers:,.0f}")
    
    st.divider()

    # 5. Visuals Row (Line Chart, Donut)
    v1, v2 = st.columns([2, 1])
    
    # Revenue Trend line chart
    trend_df = df_all.resample('W', on='Order Date')['Revenue'].sum().reset_index()
    v1.plotly_chart(px.line(trend_df, x='Order Date', y='Revenue', 
                            title="Revenue Trend Over Time (Weekly)",
                            template="plotly_dark" if st.session_state.get('dark_mode') else "plotly_white"), 
                   use_container_width=True)
    
    # New vs Returning Donut
    if not df_customers.empty:
        v2.plotly_chart(px.pie(df_customers, names='Segment', hole=0.6, title="Customer Segments Breakdown",
                               color_discrete_sequence=px.colors.qualitative.Bold),
                       use_container_width=True)
    
    # 6. Top 10 Products (Bar Chart)
    if 'Product Name' in df_all.columns:
        top_products = df_all.groupby('Product Name')['Revenue'].sum().sort_values(ascending=False).head(10).reset_index()
        st.plotly_chart(px.bar(top_products, x='Revenue', y='Product Name', orientation='h', 
                               title="Top 10 Products by Revenue (Selected Period)",
                               color='Revenue', color_continuous_scale='Blues'),
                       use_container_width=True)

    # 7. "Needs Attention" Section - At Risk Customers
    st.subheader("🔔 Needs Attention: Re-engagement List")
    at_risk = df_customers[df_customers['Segment'] == 'At Risk'].copy()
    if not at_risk.empty:
        at_risk['Email'] = at_risk['Email'].apply(mask_email)
        # Display simplified table
        st.dataframe(at_risk[['Customer_ID', 'Email', 'Total_Spent', 'Recency', 'AOV']].sort_values('Total_Spent', ascending=False), 
                     use_container_width=True)
    else:
        st.info("No customers currently meet 'At Risk' criteria for this period.")

    # 8. Data Table - Recent Orders & CSV Download
    st.subheader("📑 Recent Orders Explorer")
    recent_df = df_all.sort_values('Order Date', ascending=False).head(50).copy()
    if 'Email' in recent_df.columns:
        recent_df['Email'] = recent_df['Email'].apply(mask_email)
        
    st.dataframe(recent_df, use_container_width=True)
    
    csv_data = df_all.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Filtered Data as CSV", data=csv_data, file_name=f"Sales_Export_{datetime.now().strftime('%Y%m%d')}.csv")
