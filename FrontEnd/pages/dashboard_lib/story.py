import pandas as pd
import streamlit as st
from .data_helpers import sum_order_level_revenue, build_order_level_dataset

def render_dashboard_story(df_sales: pd.DataFrame, df_customers: pd.DataFrame, ml_bundle: dict):
    if df_sales.empty:
        return
    total_revenue = sum_order_level_revenue(df_sales)
    order_df = build_order_level_dataset(df_sales)
    total_orders = order_df["order_id"].nunique()
    aov = total_revenue / total_orders if total_orders else 0
    days_in_window = (df_sales["order_date"].max() - df_sales["order_date"].min()).days + 1 if not df_sales.empty else 1
    
    narrative = []
    if total_revenue > 0:
        avg_daily = total_revenue / days_in_window if days_in_window > 0 else total_revenue
        narrative.append(f"In this period, your store has generated <b>TK {total_revenue:,.0f}</b> in revenue, averaging <b>TK {avg_daily:,.0f}</b> per day.")
    if not df_customers.empty and "segment" in df_customers.columns:
        vips = len(df_customers[df_customers["segment"] == "VIP"])
        if vips > 0:
            narrative.append(f"Your <b>{vips} VIP customers</b> continue to represent the most stable growth lever in this window.")
    forecast = ml_bundle.get("forecast", pd.DataFrame())
    if not forecast.empty and "forecast_7d_revenue" in forecast.columns:
        next_week_rev = forecast["forecast_7d_revenue"].sum()
        narrative.append(f"The ML engine predicts a rolling 7-day revenue outlook of <b>TK {next_week_rev:,.0f}</b> based on current trajectories.")
    anomalies = ml_bundle.get("anomalies", pd.DataFrame())
    if not anomalies.empty:
        spike_count = len(anomalies)
        if spike_count > 0:
            narrative.append(f"Detected <b>{spike_count} unexpected traffic/sales spikes</b> which should be cross-referenced with your marketing schedule.")

    st.markdown(
        f"""
        <div class="bi-commentary">
            <div class="bi-commentary-label">Operational Storytelling</div>
            <div class="bi-audit-body">
                {'<br><br>'.join(narrative)}
            </div>
            <div class="bi-kpi-note" style="margin-top:1.2rem; background:var(--primary-light, rgba(79, 70, 229, 0.05)); border:1px dashed var(--primary-border, rgba(79, 70, 229, 0.2)); color:var(--primary);">
                💡 Tip: Revenue is counted using order-level totals to ensure 100% accuracy in multi-item checkouts.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
