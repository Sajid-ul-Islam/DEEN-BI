import streamlit as st
import pandas as pd
import plotly.express as px
from BackEnd.services.ts_forecast import generate_forecasts

def render_operational_forecast(df_sales: pd.DataFrame):
    """
    Renders a specialized ML forecasting block for the Operational Live view.
    Focuses on Revenue and Order Volume predictions for the next 7 days.
    """
    st.markdown("#### 🤖 Operational Analytics & Forecasts")
    
    if df_sales.empty:
        st.info("Insufficient data for operational forecasting.")
        return

    try:
        # Pre-flight check
        import statsmodels
        import sklearn
    except (ImportError, ModuleNotFoundError):
        st.info("💡 **Ensembles Offline**: Specialized ML dependencies are missing. Install `statsmodels` and `scikit-learn` to enable operational forecasting.")
        return

    # Aggregate specifically for forecasting
    daily = df_sales.groupby(df_sales["order_date"].dt.normalize(), as_index=False).agg(
        revenue=("order_total", "sum"),
        orders=("order_id", "nunique"),
        units=("qty", "sum")
    )
    
    if len(daily) < 14:
        st.info("⚠️ Operational Forecasting requires at least 14 days of history to activate ensembles.")
        return

    metrics = {"revenue": "Revenue (TK)", "orders": "Order Volume"}
    c1, c2 = st.columns(2)
    cols = [c1, c2]

    for i, (metric_key, metric_title) in enumerate(metrics.items()):
        with cols[i]:
            with st.spinner(f"Updating {metric_title} projections..."):
                res = generate_forecasts(daily, metric=metric_key, horizon=7)
                
            if "error" in res:
                st.caption(f"Forecast: {res['error']}")
                continue
                
            y = res["history"]
            fc = res["forecasts"].get(res["best_model"])
            
            # Simplified operational plot
            plot_df = pd.concat([
                pd.DataFrame({"Date": y.index, "Value": y.values, "Stage": "Historical"}),
                pd.DataFrame({"Date": fc.index, "Value": fc.values, "Stage": "Prediction"})
            ])
            
            fig = px.line(plot_df, x="Date", y="Value", color="Stage",
                          title=f"{metric_title} Outlook",
                          color_discrete_map={"Historical": "#1E293B", "Prediction": "#4F46E5"},
                          line_shape="spline")
            
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0), template="plotly_white", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

def render_category_intelligence(df_sales: pd.DataFrame):
    """
    Renders Revenue Share (Donut) and Volume (Bar) for Category-wise items.
    """
    st.markdown("#### 📂 Category Strategy Distribution")
    
    if df_sales.empty or "Category" not in df_sales.columns:
        st.info("Category data unavailable for this selection.")
        return

    # Aggregate by category and sort for impact
    cat_df = df_sales.groupby("Category").agg(
        Revenue=("order_total", "sum"),
        Volume=("qty", "sum")
    ).reset_index()
    
    cat_df = cat_df[cat_df["Revenue"] > 0].sort_values("Revenue", ascending=False)

    if cat_df.empty:
        st.info("No categorical revenue identified.")
        return

    from FrontEnd.components import ui
    
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(ui.donut_chart(cat_df, values="Revenue", names="Category", title="Revenue Share"), use_container_width=True)
    with c2:
        # Sort by volume for the bar chart
        vol_df = cat_df.sort_values("Volume", ascending=True) # Horizontal bars sorted asc to put largest at top
        st.plotly_chart(ui.bar_chart(vol_df, x="Volume", y="Category", title="Units Sold", color_scale="Tealgrn", text_auto=".1s"), use_container_width=True)
