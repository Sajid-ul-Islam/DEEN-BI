import streamlit as st
from .woocommerce import render_woocommerce_tab
from .operations_hub import render_operations_hub_tab
from .cycle_analytics import render_cycle_analytics_tab

def render_commerce_ops_page():
    st.title("📦 Commerce Operations")
    st.caption("Consolidated logistics, sync, and business performance tracking.")

    tabs = st.tabs([
        "🔄 Data Sync (WooCommerce)",
        "🚚 Logistics & Operations",
        "🕒 Business Cycles (5 PM)"
    ])

    with tabs[0]:
        render_woocommerce_tab()
    
    with tabs[1]:
        render_operations_hub_tab()

    with tabs[2]:
        render_cycle_analytics_tab()
