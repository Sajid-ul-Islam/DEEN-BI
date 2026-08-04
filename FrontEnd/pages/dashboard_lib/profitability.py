import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from FrontEnd.components import ui
from FrontEnd.components.charts import apply_plotly_theme
from BackEnd.services.profitability_engine import calculate_contribution_margin
from FrontEnd.utils.key_manager import KeyManager


def render_profitability_tab(df_sales: pd.DataFrame):
    """Renders the Contribution Margin P&L UI Tab."""
    st.markdown("### 💰 Contribution Margin & Unit Profitability P&L")
    st.caption("Detailed P&L breakdown from Gross Sales down to Net CM2 Contribution Margin.")

    # Slider Controls
    c_ctrl1, c_ctrl2 = st.columns(2)
    with c_ctrl1:
        cogs_pct = st.slider("Assumed COGS % of Net Sales", min_value=20, max_value=70, value=45, step=5, key=KeyManager.get_key("profit", "cogs_slider")) / 100.0
    with c_ctrl2:
        courier_fee = st.slider("Avg Courier Shipping Fee per Order (৳)", min_value=60, max_value=250, value=120, step=10, key=KeyManager.get_key("profit", "courier_slider"))

    pnl = calculate_contribution_margin(df_sales, cogs_margin=cogs_pct, avg_courier_fee=courier_fee)

    if pnl["gross_sales"] == 0:
        st.info("Insufficient sales data to calculate contribution margin P&L.")
        return

    # --- KPI Cards ---
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: ui.icon_metric("Gross Sales", f"TK {pnl['gross_sales']:,.0f}", icon="💵")
    with k2: ui.icon_metric("Net Sales", f"TK {pnl['net_sales']:,.0f}", icon="🛒")
    with k3: ui.icon_metric("CM1 Profit", f"TK {pnl['cm1']:,.0f}", icon="📈", delta=f"{pnl['cm1_margin']:.1f}% CM1")
    with k4: ui.icon_metric("Opex & CAC", f"TK {(pnl['courier_cost'] + pnl['ad_spend']):,.0f}", icon="🚚")
    with k5: ui.icon_metric("CM2 Net Profit", f"TK {pnl['cm2']:,.0f}", icon="💎", delta=f"{pnl['cm2_margin']:.1f}% CM2", delta_color="normal" if pnl['cm2'] > 0 else "inverse")

    st.divider()

    # --- Waterfall P&L Chart ---
    c_left, c_right = st.columns([3, 2])

    with c_left:
        st.markdown("#### 🌊 Contribution Margin Waterfall P&L")
        
        waterfall_x = ["Gross Sales", "Return Loss", "COGS", "CM1 Profit", "Courier Fees", "Ad Spend", "CM2 Net Profit"]
        waterfall_y = [
            pnl["gross_sales"],
            -pnl["return_loss"],
            -pnl["cogs"],
            0,  # subtotal
            -pnl["courier_cost"],
            -pnl["ad_spend"],
            0   # total
        ]
        
        fig_waterfall = go.Figure(go.Waterfall(
            name="P&L",
            orientation="v",
            measure=["relative", "relative", "relative", "subtotal", "relative", "relative", "total"],
            x=waterfall_x,
            textposition="outside",
            text=[f"৳{abs(v):,.0f}" if v != 0 else "" for v in waterfall_y],
            y=waterfall_y,
            connector={"line": {"color": "rgba(255,255,255,0.3)"}},
            decreasing={"marker": {"color": "#ef4444"}},
            increasing={"marker": {"color": "#10b981"}},
            totals={"marker": {"color": "#6366f1"}}
        ))
        fig_waterfall = apply_plotly_theme(fig_waterfall)
        fig_waterfall.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_waterfall, width="stretch", key=KeyManager.get_key("profit", "pnl_waterfall"))

    with c_right:
        st.markdown("#### 💡 Profitability Diagnostics")
        insights = [
            f"📦 **COGS Impact**: COGS consumes {pnl['cogs_margin']:.1f}% of net sales revenue." if "cogs_margin" in pnl else f"📦 **CM1 Margin**: Strong {pnl['cm1_margin']:.1f}% CM1 margin before fulfillment.",
            f"🚚 **Fulfillment Cost**: Courier fees account for ৳{pnl['courier_cost']:,.0f} across all completed orders.",
            f"↩️ **Return Leakage**: Returns & partials reduced potential revenue by ৳{pnl['return_loss']:,.0f}.",
            f"💎 **Final CM2 Yield**: {pnl['cm2_margin']:.1f}% net profit margin remaining after all operational expenses."
        ]
        ui.commentary("P&L Intelligence", insights)

    st.divider()

    # --- Product Profitability Leaderboard ---
    st.markdown("#### 🏆 Product Profitability Leaderboard (CM1 Ranking)")
    prod_df = pnl["product_profitability"]
    if not prod_df.empty:
        st.dataframe(
            prod_df.rename(
                columns={
                    "item_name": "Product Name",
                    "units_sold": "Units Sold",
                    "gross_revenue": "Gross Revenue (৳)",
                    "est_cogs": "Est. COGS (৳)",
                    "cm1_profit": "CM1 Profit (৳)",
                    "cm1_margin_%": "CM1 Margin %"
                }
            ),
            use_container_width=True,
            height=320
        )
