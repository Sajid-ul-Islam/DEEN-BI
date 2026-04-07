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

    # 4. VIP Churn Watch (Strategic)
    at_risk_vips = []
    if not df_customers.empty and "recency_days" in df_customers.columns:
        # VIPs who haven't bought in 21+ days
        vips_raw = df_customers[df_customers["segment"] == "VIP"]
        at_risk_vips = vips_raw[vips_raw["recency_days"] > 21].copy()
        if not at_risk_vips.empty:
            narrative.append(f"<b>{len(at_risk_vips)} VIP customers</b> are currently at risk of churning (no purchase in 21+ days).")

    # 5. Bundle Discovery (Growth)
    bundle_suggestions = []
    if not df_sales.empty:
        # Find orders with > 1 item
        multi_item_orders = df_sales.groupby("order_id").filter(lambda x: x["item_name"].nunique() > 1)
        if not multi_item_orders.empty:
            # Simple co-occurrence count
            from itertools import combinations
            order_items = multi_item_orders.groupby("order_id")["item_name"].apply(list)
            pairs = []
            for items in order_items:
                pairs.extend(combinations(sorted(items), 2))
            
            if pairs:
                pair_counts = pd.Series(pairs).value_counts()
                top_pair = pair_counts.index[0]
                if pair_counts.iloc[0] > 1: # Only suggest if seen more than once
                    narrative.append(f"Growth Slot: Customers frequently buy <b>{top_pair[0]}</b> and <b>{top_pair[1]}</b> together. Consider a bundle.")
                    bundle_suggestions = [top_pair]

    # 6. Dead Stock Detection (Efficiency)
    # Note: In a real scenario, this matches against the full inventory list.
    # We can highlight items with declining volume relative to the start of the window.
    # For now, let's identify unique items that were significantly lower in volume than usual if we have enough data.
    # Better: Identify items that appeared in previous 30 days but NOT in this window.
    # Simplified version for storytelling impact:
    dead_stock_found = []
    # If using Executive data, check for items with 0 sales in this window but high stock in recent history
    # For now, we'll flag any top category that is seeing a >50% drop.
    
    combined_narrative = " ".join(narrative).replace("<b>", "").replace("</b>", "")
    import hashlib
    narrative_hash = hashlib.md5(combined_narrative.encode()).hexdigest()[:8]
    typing_duration = max(8, len(combined_narrative) // 12)

    # Layout for Typewriter + Icon (Balanced ratio to prevent overlap)
    story_col, icon_col = st.columns([12, 1])
    
    with story_col:
        st.markdown(
            f"""
            <style>
                @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500&display=swap');

                .orthodox-typewriter {{
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.9rem;
                    background: var(--surface);
                    padding: 12px 18px;
                    border-radius: 4px;
                    border-left: 4px solid #F59E0B;
                    overflow-x: auto;
                    white-space: nowrap;
                    display: block;
                    width: 100%;
                    scrollbar-width: thin;
                    animation: 
                        typing_{narrative_hash} {typing_duration}s steps({len(combined_narrative)}, end) forwards,
                        blink-caret .75s step-end infinite;
                }}

                /* Light/Dark adaptive colors */
                @media (prefers-color-scheme: light) {{ .orthodox-typewriter {{ color: #000000; border-left-color: #000000; }} }}
                @media (prefers-color-scheme: dark) {{ .orthodox-typewriter {{ color: #F59E0B; border-left-color: #F59E0B; }} }}

                @keyframes typing_{narrative_hash} {{ from {{ width: 0 }} to {{ width: 100% }} }}
                @keyframes blink-caret {{ from, to {{ border-color: transparent }} 50% {{ border-color: inherit; }} }}
            </style>
            <div class="orthodox-typewriter" id="story-typewriter-{narrative_hash}">
                {combined_narrative}
            </div>
            """,
            unsafe_allow_html=True
        )

    # 7. Anomaly & Discovery Calculations
    daily_vol = df_sales.groupby(df_sales["order_date"].dt.date)["order_id"].nunique()
    avg_vol = daily_vol.mean()
    spikes = daily_vol[daily_vol > (avg_vol * 1.5)]
    
    # 8. Interactive Discovery Tools (Icon Bar)
    # Ensure icons appear if any insight is available (Spikes, VIP Churn, or Bundles)
    has_insights = not spikes.empty or not at_risk_vips.empty or bool(bundle_suggestions)
    
    if has_insights:
        with icon_col:
            # Use a container with a delayed fade-in to match typing duration
            st.markdown(
                f"""
                <style>
                    .delayed-icon {{
                        animation: fadeIn 0.5s ease-in forwards;
                        animation-delay: {typing_duration}s;
                        opacity: 0;
                        display: flex;
                        gap: 8px;
                    }}
                    @keyframes fadeIn {{
                        from {{ opacity: 0; }}
                        to {{ opacity: 1; }}
                    }}
                </style>
                <div class="delayed-icon">
                """,
                unsafe_allow_html=True
            )
            
            if not spikes.empty:
                if st.button("🔍", key="btn_spike_analysis", help="Deep-Dive Spike Analysis"):
                    st.session_state.show_spike_analysis = not st.session_state.get("show_spike_analysis", False)
            
            if not at_risk_vips.empty:
                if st.button("👥", key="btn_vip_churn", help="View At-Risk VIPs"):
                    st.session_state.show_vip_churn = not st.session_state.get("show_vip_churn", False)

            if bundle_suggestions:
                if st.button("💎", key="btn_bundle_suggest", help="View Bundle Strategy"):
                    st.session_state.show_bundle_suggest = not st.session_state.get("show_bundle_suggest", False)

            st.markdown("</div>", unsafe_allow_html=True)
            
            if st.session_state.get("show_spike_analysis"):
                st.markdown("---")
                st.info(f"Anomaly Detection: Baseline identified at {avg_vol:.1f} orders/day.")
                
                # Visual Spike Analysis
                c1, c2 = st.columns([2, 1])
                with c1:
                    spike_dates = [d.strftime("%Y-%m-%d") for d in spikes.index]
                    st.write(f"**Anomaly Dates:** {', '.join(spike_dates)}")
                    
                    df_spikes = df_sales[df_sales["order_date"].dt.date.isin(spikes.index)]
                    top_spike_items = df_spikes.groupby("item_name")["qty"].sum().sort_values(ascending=False).head(5)
                    st.write("**Top Products during Spikes:**")
                    st.dataframe(top_spike_items, use_container_width=True)
                
                with c2:
                    st.write("**Impact Summary**")
                    spike_rev = df_spikes["order_total"].sum()
                    st.metric("Spike Revenue", f"৳{spike_rev:,.0f}")

            # VIP Churn Rescue View
            if st.session_state.get("show_vip_churn") and not at_risk_vips.empty:
                st.markdown("---")
                st.warning(f"🚨 At-Risk VIPs: These customers are high-value but haven't interacted in 21+ days.")
                st.dataframe(at_risk_vips[["primary_name", "total_revenue", "total_orders", "recency_days"]].rename(
                    columns={"primary_name": "Customer", "total_revenue": "Lifetime Value", "recency_days": "Days Since Last Order"}
                ), use_container_width=True, hide_index=True)
                st.caption("💡 Suggestion: Launch a 'We Miss You' WhatsApp campaign for these specific individuals.")

            # Bundle Discovery View
            if st.session_state.get("show_bundle_suggest") and bundle_suggestions:
                st.markdown("---")
                st.success(f"💎 Growth Opportunity: Intelligent Product Bundling")
                pair = bundle_suggestions[0]
                st.markdown(f"**Suggested Bundle:** {pair[0]} + {pair[1]}")
                st.info("Strategy: Offering these as a single 'Essential Set' with a 5% discount can increase average transaction value without increasing marketing spend.")
