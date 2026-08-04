import streamlit as st
import pandas as pd
import plotly.express as px
from FrontEnd.components import ui
from FrontEnd.components.charts import apply_plotly_theme
from BackEnd.services.affinity_engine import MarketBasketEngine
from FrontEnd.utils.key_manager import KeyManager


def render_bundle_matrix_tab(df_sales: pd.DataFrame):
    """Renders the Market Basket & Smart Bundle Recommendation Matrix Tab."""
    st.markdown("### 🧺 Market Basket & Smart Bundle Recommendation Matrix")
    st.caption("Uncover product co-occurrence patterns, cross-sell affinities, and high-converting combo bundle suggestions.")

    engine = MarketBasketEngine(df_sales)
    rules_df = engine.get_associations(min_support=0.001, min_lift=1.05)

    if rules_df.empty:
        st.info("Insufficient basket co-occurrence data to generate association rules. Requires orders with multiple line items.")
        return

    # --- Top Affinities Summary ---
    top_rule = rules_df.iloc[0]
    total_rules = len(rules_df)

    k1, k2, k3, k4 = st.columns(4)
    with k1: ui.icon_metric("Discovered Pair Rules", f"{total_rules:,}", icon="🔗")
    with k2: ui.icon_metric("Strongest Lift Pair", f"{top_rule['Antecedent'][:16]}...", icon="🎯", delta=f"{top_rule['Lift']:.2f}x lift")
    with k3: ui.icon_metric("Highest Confidence Pair", f"{rules_df.sort_values('Confidence', ascending=False).iloc[0]['Antecedent'][:16]}...", icon="⚡", delta=f"{rules_df['Confidence'].max()*100:.1f}% CVR")
    with k4: ui.icon_metric("Avg Basket Lift", f"{rules_df['Lift'].mean():.2f}x", icon="🚀")

    st.divider()

    # --- Top 5 Smart Bundle Recommendations ---
    st.markdown("#### 🎁 AI Recommended Smart Combo Bundles")
    st.caption("Pair items with high Lift and Confidence for 2-pack/3-pack promotional campaigns to boost AOV.")

    top_bundles = rules_df.head(5)
    cols = st.columns(min(len(top_bundles), 3))
    for idx, (_, row) in enumerate(top_bundles.head(3).iterrows()):
        with cols[idx]:
            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(99, 102, 241, 0.03) 100%); 
                            border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 12px; padding: 16px; margin-bottom: 12px;">
                    <div style="font-weight: 800; color: var(--primary); font-size: 0.8rem; letter-spacing: 1px; margin-bottom: 6px;">
                        RECOMMENDED COMBO #{idx+1}
                    </div>
                    <div style="font-size: 1rem; font-weight: 700; color: white; margin-bottom: 8px;">
                        📦 {row['Antecedent']} <br><span style="color: #10b981;">+</span> {row['Consequent']}
                    </div>
                    <div style="font-size: 0.85rem; color: #9ca3af;">
                        ⚡ Lift Strength: <b>{row['Lift']:.2f}x</b><br>
                        🎯 Confidence: <b>{(row['Confidence']*100):.1f}%</b><br>
                        🛒 Pair Orders: <b>{int(row['Frequency']):,} times</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.divider()

    # --- Visual Scatter of Lift vs Confidence ---
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🎯 Association Rule Strength (Lift vs Confidence)")
        fig_scatter = px.scatter(
            rules_df.head(40),
            x="Confidence",
            y="Lift",
            size="Frequency",
            color="Lift",
            hover_data=["Antecedent", "Consequent"],
            color_continuous_scale="Viridis",
            title="Product Affinity Strength Matrix"
        )
        fig_scatter = apply_plotly_theme(fig_scatter)
        fig_scatter.update_layout(height=340, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_scatter, width="stretch", key=KeyManager.get_key("bundle", "scatter_lift"))

    with c2:
        st.markdown("#### 📊 Top Antecedent Product Triggers")
        top_triggers = rules_df.groupby("Antecedent", as_index=False)["Frequency"].sum().sort_values("Frequency", ascending=False).head(8)
        fig_triggers = px.bar(
            top_triggers,
            x="Frequency",
            y="Antecedent",
            orientation="h",
            text_auto=True,
            color="Frequency",
            color_continuous_scale="Teal",
            title="Most Frequent Basket Driver Items"
        )
        fig_triggers = apply_plotly_theme(fig_triggers)
        fig_triggers.update_layout(height=340, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig_triggers, width="stretch", key=KeyManager.get_key("bundle", "bar_triggers"))

    st.divider()

    # --- Full Association Rule Matrix Table ---
    st.markdown("#### 📋 Complete Product Association Rules Table")
    formatted_rules = rules_df.copy()
    formatted_rules["Support"] = (formatted_rules["Support"] * 100).map("{:.2f}%".format)
    formatted_rules["Confidence"] = (formatted_rules["Confidence"] * 100).map("{:.1f}%".format)
    formatted_rules["Lift"] = formatted_rules["Lift"].map("{:.2f}x".format)

    st.dataframe(
        formatted_rules[["Antecedent", "Consequent", "Frequency", "Confidence", "Lift", "Support"]].rename(
            columns={
                "Antecedent": "If Customer Buys...",
                "Consequent": "They Also Buy...",
                "Frequency": "Co-Occurrences",
                "Confidence": "Confidence %",
                "Lift": "Lift Factor",
                "Support": "Basket Support %"
            }
        ),
        use_container_width=True,
        height=320
    )
