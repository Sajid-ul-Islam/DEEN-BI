import streamlit as st
import pandas as pd
import plotly.express as px
from FrontEnd.components import ui
from FrontEnd.components.charts import apply_plotly_theme
from BackEnd.services.variant_analytics import analyze_variant_velocity
from FrontEnd.utils.key_manager import KeyManager


def render_variant_matrix_tab(df_sales: pd.DataFrame, stock_df: pd.DataFrame = None):
    """Renders the Size & Color Variant Matrix UI Tab."""
    st.markdown("### 📏 Variant Velocity & Stockout Risk Matrix")
    st.caption("High-resolution breakdown of size demand, color popularity, and variant stockout risks.")

    data = analyze_variant_velocity(df_sales, stock_df)
    variant_df = data["variant_df"]
    size_sum = data["size_summary"]
    color_sum = data["color_summary"]
    alerts = data["stockout_alerts"]

    if variant_df.empty:
        st.info("Insufficient variant data to compute size/color metrics.")
        return

    # --- KPI Overview ---
    total_variants = len(variant_df)
    critical_alerts = len(alerts)
    top_size = size_sum.iloc[0]["size"] if not size_sum.empty else "N/A"
    top_color = color_sum.iloc[0]["color"] if not color_sum.empty else "N/A"

    k1, k2, k3, k4 = st.columns(4)
    with k1: ui.icon_metric("Active SKUs", f"{total_variants:,}", icon="🏷️")
    with k2: ui.icon_metric("Top Size", top_size, icon="👕")
    with k3: ui.icon_metric("Top Color", top_color, icon="🎨")
    with k4: ui.icon_metric("Stockout Risk SKUs", f"{critical_alerts:,}", icon="⚠️", delta_color="inverse" if critical_alerts > 0 else "normal")

    st.divider()

    # --- Stockout Alert Table ---
    if not alerts.empty:
        st.markdown("#### 🚨 Urgent Variant Re-order Alerts (Stock < 7 Days)")
        st.dataframe(
            alerts[["clean_name", "color", "size", "Category", "stock_qty", "daily_velocity", "days_of_stock", "sell_through_rate"]].rename(
                columns={
                    "clean_name": "Product",
                    "color": "Color",
                    "size": "Size",
                    "stock_qty": "Stock",
                    "daily_velocity": "Daily Velocity",
                    "days_of_stock": "Days Left",
                    "sell_through_rate": "STR %"
                }
            ),
            use_container_width=True,
            height=200
        )
        st.divider()

    # --- Size & Color Charts ---
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 📐 Size Demand Share")
        if not size_sum.empty:
            fig_size = px.bar(
                size_sum,
                x="size",
                y="units_sold",
                text_auto=True,
                color="units_sold",
                color_continuous_scale="Blues",
                title="Units Sold by Size"
            )
            fig_size = apply_plotly_theme(fig_size)
            fig_size.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig_size, width="stretch", key=KeyManager.get_key("variant", "size_bar"))
        else:
            st.info("No size distribution available.")

    with c2:
        st.markdown("#### 🎨 Top 10 Color Popularity")
        if not color_sum.empty:
            fig_color = px.pie(
                color_sum.head(10),
                values="units_sold",
                names="color",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Prism,
                title="Top Color Volume Mix"
            )
            fig_color = apply_plotly_theme(fig_color)
            fig_color.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_color, width="stretch", key=KeyManager.get_key("variant", "color_pie"))
        else:
            st.info("No color distribution available.")

    st.divider()

    # --- Variant Table Search ---
    st.markdown("#### 🔍 Full SKU Variant Velocity Matrix")
    st.dataframe(
        variant_df[["clean_name", "Category", "color", "size", "total_sold", "total_revenue", "stock_qty", "daily_velocity", "sell_through_rate"]].rename(
            columns={
                "clean_name": "Product Name",
                "total_sold": "Units Sold",
                "total_revenue": "Revenue (৳)",
                "stock_qty": "Stock",
                "daily_velocity": "Daily Velocity",
                "sell_through_rate": "STR %"
            }
        ).sort_values("Units Sold", ascending=False),
        use_container_width=True,
        height=350
    )
