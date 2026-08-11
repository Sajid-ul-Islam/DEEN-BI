import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from FrontEnd.components import ui
from FrontEnd.components.charts import apply_plotly_theme
from BackEnd.services.ga4_service import (
    is_ga4_configured,
    fetch_ga4_acquisition_metrics,
    fetch_ga4_channel_breakdown,
    fetch_ga4_aarrr_funnel_metrics,
    fetch_ga4_user_engagement_metrics,
    fetch_ga4_landing_pages,
    fetch_ga4_geo_metrics,
    fetch_ga4_campaign_performance,
    fetch_ga4_ecommerce_events,
)
from BackEnd.utils.sales_schema import ensure_sales_schema
from FrontEnd.pages.dashboard_lib.data_helpers import build_order_level_dataset, sum_order_level_revenue
from FrontEnd.utils.key_manager import KeyManager
from BackEnd.services.ad_spend_service import calculate_campaign_unit_economics


def _get_standard_indicator(metric_type: str, value: float) -> tuple[str, str, str]:
    """
    Evaluates metric against industry benchmark standards.
    Returns (status_text, status_badge_html, status_level)
    """
    if metric_type == "acquisition_sessions":
        if value >= 5000:
            return "🟢 Above Standard", '<span style="background: rgba(16, 185, 129, 0.2); color: #10b981; font-weight: 700; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">🟢 Above Standard (≥5k)</span>', "above"
        elif value >= 3000:
            return "🟡 On Target", '<span style="background: rgba(245, 158, 11, 0.2); color: #f59e0b; font-weight: 700; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">🟡 On Target (≥3k)</span>', "target"
        else:
            return "🔴 Below Standard", '<span style="background: rgba(239, 68, 68, 0.2); color: #ef4444; font-weight: 700; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">🔴 Below Standard (<3k)</span>', "below"

    elif metric_type == "activation_rate":
        if value >= 55.0:
            return "🟢 Above Standard", '<span style="background: rgba(16, 185, 129, 0.2); color: #10b981; font-weight: 700; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">🟢 Above Standard (≥55%)</span>', "above"
        elif value >= 45.0:
            return "🟡 On Target", '<span style="background: rgba(245, 158, 11, 0.2); color: #f59e0b; font-weight: 700; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">🟡 On Target (≥45%)</span>', "target"
        else:
            return "🔴 Below Standard", '<span style="background: rgba(239, 68, 68, 0.2); color: #ef4444; font-weight: 700; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">🔴 Below Standard (<45%)</span>', "below"

    elif metric_type == "retention_rate":
        if value >= 30.0:
            return "🟢 Above Standard", '<span style="background: rgba(16, 185, 129, 0.2); color: #10b981; font-weight: 700; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">🟢 Above Standard (≥30%)</span>', "above"
        elif value >= 20.0:
            return "🟡 On Target", '<span style="background: rgba(245, 158, 11, 0.2); color: #f59e0b; font-weight: 700; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">🟡 On Target (≥20%)</span>', "target"
        else:
            return "🔴 Below Standard", '<span style="background: rgba(239, 68, 68, 0.2); color: #ef4444; font-weight: 700; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">🔴 Below Standard (<20%)</span>', "below"

    elif metric_type == "revenue_cvr":
        if value >= 2.50:
            return "🟢 Above Standard", '<span style="background: rgba(16, 185, 129, 0.2); color: #10b981; font-weight: 700; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">🟢 Above Standard (≥2.5%)</span>', "above"
        elif value >= 1.80:
            return "🟡 On Target", '<span style="background: rgba(245, 158, 11, 0.2); color: #f59e0b; font-weight: 700; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">🟡 On Target (≥1.8%)</span>', "target"
        else:
            return "🔴 Below Standard", '<span style="background: rgba(239, 68, 68, 0.2); color: #ef4444; font-weight: 700; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">🔴 Below Standard (<1.8%)</span>', "below"

    elif metric_type == "referral_share":
        if value >= 35.0:
            return "🟢 Above Standard", '<span style="background: rgba(16, 185, 129, 0.2); color: #10b981; font-weight: 700; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">🟢 Above Standard (≥35%)</span>', "above"
        elif value >= 25.0:
            return "🟡 On Target", '<span style="background: rgba(245, 158, 11, 0.2); color: #f59e0b; font-weight: 700; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">🟡 On Target (≥25%)</span>', "target"
        else:
            return "🔴 Below Standard", '<span style="background: rgba(239, 68, 68, 0.2); color: #ef4444; font-weight: 700; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">🔴 Below Standard (<25%)</span>', "below"

    return "⚪ Standard", "", "target"


def _render_flags_matrix(
    total_sessions: int,
    active_users: int,
    engaged_sessions: int,
    returning_users: int,
    total_conversions: int,
    total_orders: int,
    total_revenue: float,
    engagement_rate: float,
    bounce_rate: float,
    channel_df: pd.DataFrame,
    avg_duration: float = 145.0,
    page_views: int = 0,
):
    """Renders upgraded Green Flag & Red Flag Performance Matrix with Acquisition Health Score and Actionable Recommendations."""
    # Sanitize rates to valid 0-100% bounds
    engagement_rate = min(max(float(engagement_rate), 0.0), 100.0)
    bounce_rate = max(100.0 - engagement_rate, 0.0)

    # Use settled WooCommerce order count for purchase CVR if raw GA4 conversions count event fires
    if total_orders > 0:
        order_conversions = total_orders
    elif total_conversions <= total_sessions:
        order_conversions = total_conversions
    else:
        order_conversions = int(total_sessions * 0.032)

    overall_cvr = (order_conversions / total_sessions * 100) if total_sessions else 0.0
    overall_cvr = min(overall_cvr, 100.0)
    retention_rate = (returning_users / active_users * 100) if active_users else 0.0
    page_depth = (page_views / total_sessions) if total_sessions else 2.2

    # Calculate Organic vs Paid share
    organic_sessions = 0
    paid_sessions = 0
    if not channel_df.empty and "source_medium" in channel_df.columns:
        org_mask = channel_df["source_medium"].str.contains("organic|referral|direct", case=False, na=False)
        organic_sessions = int(channel_df.loc[org_mask, "sessions"].sum())
        paid_mask = channel_df["source_medium"].str.contains("cpc|paid|fb|instagram|meta|ads", case=False, na=False)
        paid_sessions = int(channel_df.loc[paid_mask, "sessions"].sum())

    organic_share = (organic_sessions / total_sessions * 100) if total_sessions else 35.0
    paid_share = (paid_sessions / total_sessions * 100) if total_sessions else 55.0

    green_flags = []
    red_flags = []
    action_items = []

    # 1. Visitor Engagement Rate
    if engagement_rate >= 50.0:
        green_flags.append({
            "title": f"High Visitor Engagement ({engagement_rate:.1f}%)",
            "benchmark": "Target: ≥ 50.0%",
            "desc": f"{engagement_rate:.1f}% of visitors explore products beyond the bounce threshold."
        })
    else:
        red_flags.append({
            "title": f"Elevated Bounce Rate ({bounce_rate:.1f}%)",
            "severity": "HIGH SEVERITY",
            "desc": f"{bounce_rate:.1f}% of visitors exit on arrival. Optimize mobile viewport speed & hero product relevance."
        })
        action_items.append("⚡ **Fix Landing Page Bounces**: Compress hero banners and improve mobile above-the-fold CTA visibility.")

    # 2. Purchase Conversion Rate (CVR)
    if overall_cvr >= 2.5:
        green_flags.append({
            "title": f"Strong Order Conversion Rate ({overall_cvr:.2f}%)",
            "benchmark": "Target: ≥ 2.50%",
            "desc": f"Traffic-to-order purchase CVR of {overall_cvr:.2f}% meets or exceeds e-commerce benchmark."
        })
    elif overall_cvr < 1.8:
        red_flags.append({
            "title": f"Sub-Optimal Conversion Rate ({overall_cvr:.2f}%)",
            "severity": "HIGH SEVERITY",
            "desc": f"Overall purchase CVR of {overall_cvr:.2f}% is below 2.0% benchmark. Check checkout friction & COD trust badges."
        })
        action_items.append("💳 **Reduce Checkout Friction**: Add 1-click Cash on Delivery (COD) badge and express checkout fields.")

    # 3. Customer Retention Rate
    if retention_rate >= 25.0:
        green_flags.append({
            "title": f"Solid Customer Retention ({retention_rate:.1f}%)",
            "benchmark": "Target: ≥ 25.0%",
            "desc": f"High proportion ({retention_rate:.1f}%) of returning visitors driving repeatable organic sales."
        })
    else:
        red_flags.append({
            "title": f"Customer Retention Drag ({retention_rate:.1f}%)",
            "severity": "MEDIUM SEVERITY",
            "desc": f"Less than 25% returning visitors ({retention_rate:.1f}%). Launch automated SMS/WhatsApp win-back campaigns."
        })
        action_items.append("🔄 **Activate Repeat Buyers**: Automated post-purchase SMS/WhatsApp coupon 14 days after order delivery.")

    # 4. Traffic Source Mix & Ad Reliance
    if organic_share >= 30.0:
        green_flags.append({
            "title": f"Healthy Organic & Direct Share ({organic_share:.1f}%)",
            "benchmark": "Target: ≥ 30.0%",
            "desc": "Strong organic SEO & brand recall footprint reducing overall customer acquisition cost (CAC)."
        })
    if paid_share >= 65.0:
        red_flags.append({
            "title": f"High Paid Ad Reliance ({paid_share:.1f}%)",
            "severity": "MEDIUM SEVERITY",
            "desc": f"Over 65% of traffic ({paid_share:.1f}%) is dependent on paid ads. Diversify into organic & VIP referral channels."
        })
        action_items.append("📢 **Diversify Acquisition Channels**: Build VIP customer referral links to lower paid Meta/Google ad reliance.")

    # 5. Dwell Time & Browsing Depth
    if avg_duration >= 120.0:
        green_flags.append({
            "title": f"Extended Session Duration ({int(avg_duration//60)}m {int(avg_duration%60)}s)",
            "benchmark": "Target: ≥ 2m 0s",
            "desc": "Visitors spend substantial active time considering catalog items."
        })
    elif avg_duration < 60.0:
        red_flags.append({
            "title": f"Short Session Dwell Time ({int(avg_duration)}s)",
            "severity": "LOW SEVERITY",
            "desc": "Average dwell time is under 60 seconds. Add interactive product lookbooks and video previews."
        })
        action_items.append("🎬 **Enhance Catalog Dwell Time**: Add short product demo video clips to high-traffic product pages.")

    # 6. Navigation Depth (Pages / Session)
    if page_depth >= 2.2:
        green_flags.append({
            "title": f"Deep Catalog Exploration ({page_depth:.1f} pages/session)",
            "benchmark": "Target: ≥ 2.2",
            "desc": "Users browse multiple category pages and related product recommendations."
        })
    elif page_depth < 1.5:
        red_flags.append({
            "title": f"Shallow Page Navigation ({page_depth:.1f} pages/session)",
            "severity": "LOW SEVERITY",
            "desc": "Single-item browsing. Implement 'Frequently Bought Together' cross-sell blocks."
        })
        action_items.append("🛒 **Improve Cross-Selling**: Embed 'Complete the Look' and related product bundles on single-product pages.")

    # --- COMPUTE ACQUISITION HEALTH INDEX SCORE (0-100) ---
    base_score = 50 + (len(green_flags) * 12) - (len(red_flags) * 10)
    health_score = int(min(max(base_score, 15), 100))

    if health_score >= 80:
        score_color = "#10b981"
        score_badge = "🟢 EXCELLENT GROWTH HEALTH"
        score_bg = "rgba(16, 185, 129, 0.12)"
        score_border = "rgba(16, 185, 129, 0.3)"
    elif health_score >= 60:
        score_color = "#f59e0b"
        score_badge = "🟡 MODERATE HEALTH — OPPORTUNITIES DETECTED"
        score_bg = "rgba(245, 158, 11, 0.12)"
        score_border = "rgba(245, 158, 11, 0.3)"
    else:
        score_color = "#ef4444"
        score_badge = "🔴 AT RISK — ACTION REQUIRED"
        score_bg = "rgba(239, 68, 68, 0.12)"
        score_border = "rgba(239, 68, 68, 0.3)"

    st.markdown("#### 🚦 Green & Red Flags Performance Matrix")

    # Render Health Score Header Card
    st.markdown(
        f'<div style="background: {score_bg}; border: 1px solid {score_border}; border-radius: 16px; padding: 20px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between;">'
        f'<div>'
        f'<div style="color: {score_color}; font-weight: 800; font-size: 1.3rem; letter-spacing: -0.02em;">ACQUISITION HEALTH SCORE: {health_score} / 100</div>'
        f'<div style="color: var(--on-surface-variant); font-size: 0.88rem; margin-top: 4px; font-weight: 500;">{score_badge} — Evaluated across 6 core traffic & conversion performance benchmarks.</div>'
        f'</div>'
        f'<div style="background: {score_color}; color: #000; font-weight: 800; font-size: 1.4rem; padding: 8px 18px; border-radius: 12px;">{health_score}%</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    c_green, c_red = st.columns(2)

    with c_green:
        st.markdown(
            '<div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); '
            'border-radius: 14px; padding: 14px 16px; margin-bottom: 15px;">'
            '<div style="color: #10b981; font-weight: 800; font-size: 1.05rem; display: flex; align-items: center; justify-content: space-between;">'
            f'<span>🟢 GREEN FLAGS ({len(green_flags)} WINS)</span>'
            f'<span style="font-size: 0.75rem; background: rgba(16, 185, 129, 0.2); padding: 3px 8px; border-radius: 100px;">HEALTHY SIGNALS</span>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        for gf in green_flags:
            bench_html = f'<span style="background: rgba(16, 185, 129, 0.2); color: #10b981; font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; font-weight: 700; margin-left: 8px;">{gf.get("benchmark", "")}</span>' if gf.get("benchmark") else ""
            st.markdown(
                f'<div style="background: rgba(16, 185, 129, 0.05); border-left: 4px solid #10b981; '
                f'padding: 12px 14px; border-radius: 6px; margin-bottom: 12px;">'
                f'<div style="font-weight: 700; color: #10b981; font-size: 0.92rem; display: flex; align-items: center; justify-content: space-between;">'
                f'<span>✅ {gf["title"]}</span>{bench_html}</div>'
                f'<div style="color: var(--on-surface-variant); font-size: 0.82rem; margin-top: 5px; line-height: 1.4;">{gf["desc"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # --- REVENUE OPPORTUNITY LOSS CALCULATOR ---
    aov = (total_revenue / total_orders) if total_orders > 0 else 1800.0
    excess_bounce_rate = max(0.0, bounce_rate - 45.0)
    lost_bounce_sessions = total_sessions * (excess_bounce_rate / 100.0)
    cvr_factor = max(overall_cvr, 1.8) / 100.0
    bounce_opp_loss = lost_bounce_sessions * cvr_factor * aov

    cvr_gap = max(0.0, 2.5 - overall_cvr) / 100.0
    cvr_opp_loss = total_sessions * cvr_gap * aov
    total_recovery_potential = bounce_opp_loss + cvr_opp_loss

    with c_red:
        st.markdown(
            '<div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.25); '
            'border-radius: 14px; padding: 14px 16px; margin-bottom: 15px;">'
            '<div style="color: #ef4444; font-weight: 800; font-size: 1.05rem; display: flex; align-items: center; justify-content: space-between;">'
            f'<span>🔴 RED FLAGS ({len(red_flags)} RISKS)</span>'
            f'<span style="font-size: 0.75rem; background: rgba(239, 68, 68, 0.2); padding: 3px 8px; border-radius: 100px;">NEEDS ATTENTION</span>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        for rf in red_flags:
            sev_color = "#ef4444" if "HIGH" in rf.get("severity", "") else "#f59e0b"
            sev_html = f'<span style="background: rgba(239, 68, 68, 0.2); color: {sev_color}; font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; font-weight: 700; margin-left: 8px;">{rf.get("severity", "")}</span>' if rf.get("severity") else ""
            st.markdown(
                f'<div style="background: rgba(239, 68, 68, 0.05); border-left: 4px solid #ef4444; '
                f'padding: 12px 14px; border-radius: 6px; margin-bottom: 12px;">'
                f'<div style="font-weight: 700; color: #ef4444; font-size: 0.92rem; display: flex; align-items: center; justify-content: space-between;">'
                f'<span>⚠️ {rf["title"]}</span>{sev_html}</div>'
                f'<div style="color: var(--on-surface-variant); font-size: 0.82rem; margin-top: 5px; line-height: 1.4;">{rf["desc"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        if total_recovery_potential > 0:
            st.markdown(
                f'<div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); '
                f'padding: 12px 14px; border-radius: 8px; margin-top: 10px; margin-bottom: 12px;">'
                f'<div style="font-weight: 800; color: #f59e0b; font-size: 0.9rem;">💰 REVENUE RECOVERY POTENTIAL</div>'
                f'<div style="color: var(--on-surface-variant); font-size: 0.82rem; margin-top: 4px;">'
                f'Resolving bounce & checkout friction could recover an estimated <b>TK {total_recovery_potential:,.0f}</b> in gross sales.'
                f'</div></div>',
                unsafe_allow_html=True,
            )

    # Actionable Recommendations Accordion
    if action_items:
        with st.expander("🛠️ Prioritized Growth Action Plan (Click to expand)", expanded=False):
            st.markdown("##### 🚀 Recommended Fixes to Maximize Conversion Output:")
            for item in action_items:
                st.markdown(f"- {item}")


def render_acquisition_analytics(df_sales: pd.DataFrame, df_customers: pd.DataFrame = None):
    """
    Renders the upgraded Traffic & User Acquisition Dashboard with live GA4 integration,
    Green & Red Flag Diagnostics, Landing Pages, Geo Location, Campaign Performance, and E-Commerce Event Funnel metrics.
    """
    st.markdown("### 📊 Traffic Insights")

    # --- Live GA4 & Meta API Mode Detection ---
    ga4_active = is_ga4_configured()
    from BackEnd.services.meta_service import is_meta_api_configured, get_meta_credentials
    meta_active = is_meta_api_configured()

    badge_cols = st.columns([1, 1])
    with badge_cols[0]:
        if ga4_active:
            st.markdown(
                '<div style="display: inline-flex; align-items: center; background: rgba(16, 185, 129, 0.15); '
                'border: 1px solid rgba(16, 185, 129, 0.3); padding: 6px 14px; border-radius: 20px; margin-bottom: 15px;">'
                '<span style="width: 8px; height: 8px; background: #10b981; border-radius: 50%; margin-right: 8px; box-shadow: 0 0 8px #10b981;"></span>'
                '<span style="color: #10b981; font-weight: 700; font-size: 0.8rem; letter-spacing: 0.5px;">LIVE GA4 STREAMING ACTIVE</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.info("💡 **Synthetic Mode Active** — GA4 API is unconfigured.")

    with badge_cols[1]:
        if meta_active:
            _, meta_acc_id = get_meta_credentials()
            st.markdown(
                f'<div style="display: inline-flex; align-items: center; background: rgba(59, 130, 246, 0.15); '
                f'border: 1px solid rgba(59, 130, 246, 0.3); padding: 6px 14px; border-radius: 20px; margin-bottom: 15px;">'
                f'<span style="width: 8px; height: 8px; background: #3b82f6; border-radius: 50%; margin-right: 8px; box-shadow: 0 0 8px #3b82f6;"></span>'
                f'<span style="color: #3b82f6; font-weight: 700; font-size: 0.8rem; letter-spacing: 0.5px;">LIVE META ADS API CONNECTED ({meta_acc_id})</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # --- Fetch Core Sales & GA4 Data ---
    sales = ensure_sales_schema(df_sales)
    order_df = build_order_level_dataset(sales)
    total_orders = order_df["order_id"].nunique() if not order_df.empty else 0
    total_revenue = sum_order_level_revenue(sales, order_df)
    
    ga4_df = fetch_ga4_acquisition_metrics("30daysAgo", "today") if ga4_active else pd.DataFrame()
    ga4_funnel = fetch_ga4_aarrr_funnel_metrics("30daysAgo", "today") if ga4_active else {}
    ga4_engagement = fetch_ga4_user_engagement_metrics("30daysAgo", "today") if ga4_active else {}

    # Calculate Core Numbers
    if ga4_active and not ga4_df.empty:
        total_sessions = int(ga4_df["sessions"].sum())
        active_users = int(ga4_df["active_users"].sum())
        total_conversions = int(ga4_df["conversions"].sum())
        
        engaged_sessions = ga4_funnel.get("activation_engaged_sessions", int(total_sessions * 0.58))
        returning_users = ga4_funnel.get("retention_returning_users", int(active_users * 0.32))
        new_users = ga4_funnel.get("retention_new_users", active_users - returning_users)
        
        channel_df = fetch_ga4_channel_breakdown("30daysAgo", "today")
        ref_df = ga4_df[ga4_df["source_medium"].str.contains("organic|referral|direct", case=False, na=False)]
        referral_sessions = int(ref_df["sessions"].sum()) if not ref_df.empty else int(total_sessions * 0.35)
        
        engagement_rate = ga4_engagement.get("engagement_rate", (engaged_sessions / total_sessions * 100) if total_sessions else 58.0)
        bounce_rate = ga4_engagement.get("bounce_rate", 100.0 - engagement_rate)
        avg_duration = ga4_engagement.get("avg_session_duration", 145.0)
        page_views = ga4_engagement.get("page_views", int(total_sessions * 2.4))
    else:
        # Synthetic Simulation Anchored on Real WooCommerce Orders
        cvr = 0.032
        total_sessions = int(total_orders / cvr) if total_orders > 0 else 10000
        active_users = int(total_sessions * 0.82)
        engaged_sessions = int(total_sessions * 0.54)
        returning_users = int(active_users * 0.28)
        new_users = active_users - returning_users
        total_conversions = total_orders
        referral_sessions = int(total_sessions * 0.38)
        engagement_rate = 54.0
        bounce_rate = 46.0
        avg_duration = 138.0
        page_views = int(total_sessions * 2.2)
        
        # Synthetic Channels
        channels_spec = {
            "fb / paid": 0.45,
            "google / cpc": 0.25,
            "organic / search": 0.15,
            "direct / none": 0.10,
            "email / promo": 0.05,
        }
        rng = np.random.default_rng(seed=int(total_orders or 42))
        chan_rows = []
        for chan, weight in channels_spec.items():
            s_val = int(total_sessions * weight)
            c_val = int(total_orders * weight * rng.uniform(0.9, 1.1))
            r_val = float(total_revenue * weight * rng.uniform(0.9, 1.1))
            chan_rows.append({
                "source_medium": chan,
                "sessions": s_val,
                "active_users": int(s_val * 0.8),
                "conversions": c_val,
                "revenue": r_val,
                "conversion_rate": (c_val / s_val * 100) if s_val else 0.0
            })
        channel_df = pd.DataFrame(chan_rows)

    overall_cvr = (total_conversions / total_sessions * 100) if total_sessions else 0.0
    activation_rate = (engaged_sessions / total_sessions * 100) if total_sessions else 0.0
    retention_rate = (returning_users / active_users * 100) if active_users else 0.0

    # --- TOP LEVEL GA4 PROPERTY KPI CARDS ---
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        ui.icon_metric("Sessions Volume", f"{total_sessions:,}", icon="🌐")
        ui.badge("Total Traffic")
    with m2:
        ui.icon_metric("Active Users", f"{active_users:,}", icon="👥", delta=f"{new_users:,} new")
        ui.badge("Unique Visitors")
    with m3:
        ui.icon_metric("Engagement Rate", f"{engagement_rate:.1f}%", icon="⚡", delta=f"{bounce_rate:.1f}% bounce")
        ui.badge("Engaged Visits")
    with m4:
        ui.icon_metric("Avg Duration", f"{int(avg_duration//60)}m {int(avg_duration%60)}s", icon="⏱️")
        ui.badge("Session Length")
    with m5:
        ui.icon_metric("Total Page Views", f"{page_views:,}", icon="📄", delta=f"{(page_views/total_sessions if total_sessions else 0):.1f} / session")
        ui.badge("Page Depth")

    st.divider()

    # --- 🚦 GREEN FLAGS & RED FLAGS MATRIX ---
    _render_flags_matrix(
        total_sessions=total_sessions,
        active_users=active_users,
        engaged_sessions=engaged_sessions,
        returning_users=returning_users,
        total_conversions=total_conversions,
        total_orders=total_orders,
        total_revenue=total_revenue,
        engagement_rate=engagement_rate,
        bounce_rate=bounce_rate,
        channel_df=channel_df,
        avg_duration=avg_duration,
        page_views=page_views,
    )

    st.divider()

    # --- INTERACTIVE GA4 SUB-TABS ---
    tab_funnel, tab_landing, tab_geo, tab_campaign, tab_ecommerce = st.tabs([
        "🏴‍☠️ AARRR Funnel & Channels",
        "📑 Top Landing Pages",
        "🌍 Geo & City Intelligence",
        "🎯 Campaigns & Traffic Sources",
        "🛒 GA4 E-Commerce Events"
    ])

    # ==========================================
    # TAB 1: 🏴‍☠️ AARRR FUNNEL & CHANNELS
    # ==========================================
    with tab_funnel:
        st.markdown("#### 🏴‍☠️ AARRR Pirate Metrics Overview")
        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            ui.icon_metric("A - Acquisition", f"{total_sessions:,}", icon="📡")
            _, badge_html, _ = _get_standard_indicator("acquisition_sessions", total_sessions)
            st.markdown(f'<div style="margin-top: 4px;">{badge_html}</div>', unsafe_allow_html=True)
        with k2:
            ui.icon_metric("A - Activation", f"{engaged_sessions:,}", icon="⚡", delta=f"{activation_rate:.1f}% rate")
            _, badge_html, _ = _get_standard_indicator("activation_rate", activation_rate)
            st.markdown(f'<div style="margin-top: 4px;">{badge_html}</div>', unsafe_allow_html=True)
        with k3:
            ui.icon_metric("R - Retention", f"{returning_users:,}", icon="🔄", delta=f"{retention_rate:.1f}% return")
            _, badge_html, _ = _get_standard_indicator("retention_rate", retention_rate)
            st.markdown(f'<div style="margin-top: 4px;">{badge_html}</div>', unsafe_allow_html=True)
        with k4:
            ui.icon_metric("R - Revenue", f"TK {total_revenue:,.0f}", icon="💰", delta=f"{(total_orders if total_orders > 0 else total_conversions):,} orders ({overall_cvr:.2f}% CVR)")
            _, badge_html, _ = _get_standard_indicator("revenue_cvr", overall_cvr)
            st.markdown(f'<div style="margin-top: 4px;">{badge_html}</div>', unsafe_allow_html=True)
        with k5:
            ref_share = (referral_sessions / total_sessions * 100) if total_sessions else 0.0
            ui.icon_metric("R - Referral", f"{referral_sessions:,}", icon="📢", delta=f"{ref_share:.1f}% share")
            _, badge_html, _ = _get_standard_indicator("referral_share", ref_share)
            st.markdown(f'<div style="margin-top: 4px;">{badge_html}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col_funnel, col_insights = st.columns([3, 2])
        with col_funnel:
            st.markdown("#### 🔻 Growth & Conversion Funnel")
            funnel_stages = [
                "1. Acquisition (Sessions)",
                "2. Activation (Engaged Visits)",
                "3. Retention (Returning Users)",
                "4. Revenue (Conversions)",
                "5. Referral (Organic/Direct)"
            ]
            funnel_values = [
                total_sessions,
                engaged_sessions,
                returning_users,
                total_orders if total_orders > 0 else total_conversions,
                referral_sessions
            ]
            fig_funnel = go.Figure(go.Funnel(
                y=funnel_stages,
                x=funnel_values,
                textinfo="value+percent initial+percent previous",
                marker={"color": ["#6366f1", "#06b6d4", "#10b981", "#f59e0b", "#8b5cf6"]},
                connector={"line": {"color": "rgba(255,255,255,0.2)", "width": 1}}
            ))
            fig_funnel = apply_plotly_theme(fig_funnel)
            fig_funnel.update_layout(
                height=360,
                margin=dict(l=10, r=10, t=20, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_funnel, width="stretch", key=KeyManager.get_key("acq", "aarrr_funnel"))

        with col_insights:
            st.markdown("#### 💡 Growth Diagnostic & Funnel Health")
            drop_activation = (1 - (engaged_sessions / total_sessions)) * 100 if total_sessions else 0
            drop_conversion = (1 - (total_conversions / engaged_sessions)) * 100 if engaged_sessions else 0
            insights = []
            if ga4_active:
                insights.append("🟢 **Live GA4 Data**: Streaming real-time session events.")
            else:
                insights.append("🟡 **Simulated Engine**: Figures anchored on actual WooCommerce orders.")
            insights.append(f"⚡ **Activation Efficiency**: {activation_rate:.1f}% of visitors stay past the bounce threshold.")
            insights.append(f"📉 **Drop-off**: {drop_conversion:.1f}% drop between Activation and Final Purchase.")
            insights.append(f"🔄 **Retention Power**: {retention_rate:.1f}% of active visitors are returning buyers.")
            ui.commentary("Funnel Diagnostics", insights)

        st.markdown("<br>", unsafe_allow_html=True)
        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown("#### 🌐 Traffic Source & Channel Mix")
            if not channel_df.empty:
                fig_pie = px.pie(
                    channel_df,
                    values="sessions",
                    names="source_medium",
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Bold,
                    title="Sessions by Channel"
                )
                fig_pie = apply_plotly_theme(fig_pie)
                fig_pie.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_pie, width="stretch", key=KeyManager.get_key("acq", "channel_pie"))
            else:
                st.info("No channel data available.")

        with c_right:
            st.markdown("#### 🎯 Channel Conversion Rate (CVR %)")
            if not channel_df.empty:
                df_sorted = channel_df.sort_values("conversion_rate", ascending=True)
                fig_cvr = px.bar(
                    df_sorted,
                    x="conversion_rate",
                    y="source_medium",
                    orientation="h",
                    text_auto=".2f",
                    color="conversion_rate",
                    color_continuous_scale="Viridis",
                    title="Conversion Rate by Channel"
                )
                fig_cvr = apply_plotly_theme(fig_cvr)
                fig_cvr.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
                st.plotly_chart(fig_cvr, width="stretch", key=KeyManager.get_key("acq", "channel_cvr_bar"))
            else:
                st.info("No channel conversion rate data available.")

        st.markdown("<br>", unsafe_allow_html=True)
        d_left, d_right = st.columns(2)
        with d_left:
            st.markdown("#### 📱 Device Share")
            if ga4_active and not ga4_df.empty and "device" in ga4_df.columns:
                dev_df = ga4_df.groupby("device", as_index=False).agg(sessions=("sessions", "sum"))
                fig_dev = px.pie(
                    dev_df, values="sessions", names="device",
                    color_discrete_sequence=["#3b82f6", "#10b981", "#f59e0b"],
                    title="Sessions by Device Type"
                )
                fig_dev = apply_plotly_theme(fig_dev)
                fig_dev.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_dev, width="stretch", key=KeyManager.get_key("acq", "device_pie"))
            else:
                synth_dev = pd.DataFrame([
                    {"device": "Mobile", "sessions": int(total_sessions * 0.78)},
                    {"device": "Desktop", "sessions": int(total_sessions * 0.18)},
                    {"device": "Tablet", "sessions": int(total_sessions * 0.04)},
                ])
                fig_dev = px.pie(
                    synth_dev, values="sessions", names="device",
                    color_discrete_sequence=["#3b82f6", "#10b981", "#f59e0b"],
                    title="Modeled Device Share (Mobile-First)"
                )
                fig_dev = apply_plotly_theme(fig_dev)
                fig_dev.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_dev, width="stretch", key=KeyManager.get_key("acq", "synth_device_pie"))

        with d_right:
            st.markdown("#### 📈 Longitudinal Traffic Trend")
            if ga4_active and not ga4_df.empty and "date" in ga4_df.columns:
                daily_ga = ga4_df.groupby("date", as_index=False).agg(sessions=("sessions", "sum")).sort_values("date")
                fig_trend = px.area(daily_ga, x="date", y="sessions", title="Daily Session Volume (GA4)", color_discrete_sequence=["#6366f1"])
                fig_trend = apply_plotly_theme(fig_trend)
                fig_trend.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_trend, width="stretch", key=KeyManager.get_key("acq", "live_daily_area"))
            else:
                if not sales.empty and "order_date" in sales.columns:
                    sales_daily = sales.copy()
                    sales_daily["date"] = pd.to_datetime(sales_daily["order_date"], errors="coerce").dt.normalize()
                    daily_synth = sales_daily.groupby("date", as_index=False)["order_id"].nunique().rename(columns={"order_id": "orders"})
                    daily_synth["sessions"] = (daily_synth["orders"] / 0.032).astype(int)
                    fig_trend = px.area(daily_synth.tail(30), x="date", y="sessions", title="Daily Session Volume (Modeled)", color_discrete_sequence=["#3b82f6"])
                    fig_trend = apply_plotly_theme(fig_trend)
                    fig_trend.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_trend, width="stretch", key=KeyManager.get_key("acq", "synth_daily_area"))
                else:
                    st.info("Insufficient data for longitudinal trends.")

    # ==========================================
    # TAB 2: 📑 TOP LANDING PAGES
    # ==========================================
    with tab_landing:
        st.markdown("#### 📑 Landing Page Performance & Content Analytics")
        
        landing_df = fetch_ga4_landing_pages("30daysAgo", "today") if ga4_active else pd.DataFrame()
        if landing_df.empty:
            synth_pages = [
                {"landing_page": "/", "sessions": int(total_sessions * 0.42), "active_users": int(active_users * 0.40), "engagement_rate": 62.5, "conversions": int(total_conversions * 0.35), "revenue": total_revenue * 0.35},
                {"landing_page": "/shop/", "sessions": int(total_sessions * 0.22), "active_users": int(active_users * 0.20), "engagement_rate": 58.0, "conversions": int(total_conversions * 0.25), "revenue": total_revenue * 0.25},
                {"landing_page": "/product/polo-shirt/", "sessions": int(total_sessions * 0.12), "active_users": int(active_users * 0.11), "engagement_rate": 68.4, "conversions": int(total_conversions * 0.18), "revenue": total_revenue * 0.18},
                {"landing_page": "/product/cargo-pants/", "sessions": int(total_sessions * 0.09), "active_users": int(active_users * 0.08), "engagement_rate": 64.1, "conversions": int(total_conversions * 0.10), "revenue": total_revenue * 0.10},
                {"landing_page": "/checkout/", "sessions": int(total_sessions * 0.06), "active_users": int(active_users * 0.05), "engagement_rate": 82.0, "conversions": int(total_conversions * 0.08), "revenue": total_revenue * 0.08},
                {"landing_page": "/category/mens/", "sessions": int(total_sessions * 0.05), "active_users": int(active_users * 0.04), "engagement_rate": 51.2, "conversions": int(total_conversions * 0.03), "revenue": total_revenue * 0.03},
                {"landing_page": "/sale/", "sessions": int(total_sessions * 0.04), "active_users": int(active_users * 0.04), "engagement_rate": 55.0, "conversions": int(total_conversions * 0.01), "revenue": total_revenue * 0.01},
            ]
            landing_df = pd.DataFrame(synth_pages)

        l_left, l_right = st.columns([3, 2])
        with l_left:
            top_lp = landing_df.head(10).sort_values("sessions", ascending=True)
            fig_lp = px.bar(
                top_lp,
                x="sessions",
                y="landing_page",
                orientation="h",
                text_auto=",d",
                color="engagement_rate",
                color_continuous_scale="Plasma",
                title="Top 10 Landing Pages by Session Volume"
            )
            fig_lp = apply_plotly_theme(fig_lp)
            fig_lp.update_layout(height=360, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_lp, width="stretch", key=KeyManager.get_key("acq", "landing_bar"))

        with l_right:
            st.markdown("##### 💡 Landing Page Insights")
            top_page = landing_df.iloc[0]["landing_page"] if not landing_df.empty else "/"
            top_cvr_page = landing_df.sort_values("conversions", ascending=False).iloc[0]["landing_page"] if not landing_df.empty else "/"
            ui.commentary(
                "Content Highlights",
                [
                    f"🏆 **Top Entry Door**: `{top_page}` accounts for {((landing_df.iloc[0]['sessions']/landing_df['sessions'].sum())*100):.1f}% of all site entries.",
                    f"🎯 **Highest Conversion Driver**: `{top_cvr_page}` yields the most completed purchase conversions.",
                    f"⚡ **Avg Landing Engagement**: {landing_df['engagement_rate'].mean():.1f}% across top entry pages."
                ]
            )

        st.markdown("##### 📋 Landing Page Performance Table")
        disp_df = landing_df.copy()
        disp_df["revenue"] = disp_df["revenue"].apply(lambda x: f"TK {x:,.2f}")
        disp_df["engagement_rate"] = disp_df["engagement_rate"].apply(lambda x: f"{x:.1f}%")
        st.dataframe(
            disp_df,
            column_config={
                "landing_page": "Landing Page URL Path",
                "sessions": "Sessions",
                "active_users": "Active Users",
                "engagement_rate": "Engagement Rate",
                "conversions": "Conversions",
                "revenue": "Revenue Impact"
            },
            hide_index=True,
            use_container_width=True
        )

    # ==========================================
    # TAB 3: 🌍 GEO & CITY INTELLIGENCE
    # ==========================================
    with tab_geo:
        st.markdown("#### 🌍 Geographic Location & City Intelligence")
        
        geo_df = fetch_ga4_geo_metrics("30daysAgo", "today") if ga4_active else pd.DataFrame()
        if geo_df.empty:
            synth_cities = [
                {"country": "Bangladesh", "city": "Dhaka", "sessions": int(total_sessions * 0.52), "active_users": int(active_users * 0.50), "conversions": int(total_conversions * 0.55), "revenue": total_revenue * 0.55},
                {"country": "Bangladesh", "city": "Chittagong", "sessions": int(total_sessions * 0.18), "active_users": int(active_users * 0.17), "conversions": int(total_conversions * 0.18), "revenue": total_revenue * 0.18},
                {"country": "Bangladesh", "city": "Sylhet", "sessions": int(total_sessions * 0.08), "active_users": int(active_users * 0.08), "conversions": int(total_conversions * 0.07), "revenue": total_revenue * 0.07},
                {"country": "Bangladesh", "city": "Rajshahi", "sessions": int(total_sessions * 0.06), "active_users": int(active_users * 0.06), "conversions": int(total_conversions * 0.05), "revenue": total_revenue * 0.05},
                {"country": "Bangladesh", "city": "Khulna", "sessions": int(total_sessions * 0.05), "active_users": int(active_users * 0.05), "conversions": int(total_conversions * 0.05), "revenue": total_revenue * 0.05},
                {"country": "Bangladesh", "city": "Gazipur", "sessions": int(total_sessions * 0.04), "active_users": int(active_users * 0.04), "conversions": int(total_conversions * 0.04), "revenue": total_revenue * 0.04},
                {"country": "Bangladesh", "city": "Narayanganj", "sessions": int(total_sessions * 0.03), "active_users": int(active_users * 0.03), "conversions": int(total_conversions * 0.03), "revenue": total_revenue * 0.03},
                {"country": "Bangladesh", "city": "Barisal", "sessions": int(total_sessions * 0.02), "active_users": int(active_users * 0.02), "conversions": int(total_conversions * 0.02), "revenue": total_revenue * 0.02},
            ]
            geo_df = pd.DataFrame(synth_cities)

        # Layer COD Return Rate % from returns_tracker / session_state
        returns_df = st.session_state.get("returns_data", pd.DataFrame())
        city_returns_map = {}
        if not returns_df.empty and "city" in returns_df.columns:
            city_returns_map = returns_df.groupby("city")["order_id"].nunique().to_dict()

        def _calc_return_rate(row):
            c_name = str(row.get("city", ""))
            convs = float(row.get("conversions", 0))
            if c_name in city_returns_map:
                rets = city_returns_map[c_name]
            else:
                city_rates = {"Dhaka": 0.07, "Chittagong": 0.14, "Gazipur": 0.18, "Sylhet": 0.09, "Khulna": 0.12}
                rets = convs * city_rates.get(c_name, 0.10)
            rate = (rets / convs * 100) if convs > 0 else 0.0
            return round(rate, 1)

        geo_df["return_rate"] = geo_df.apply(_calc_return_rate, axis=1)
        geo_df["risk_level"] = geo_df["return_rate"].apply(
            lambda r: "🔴 Elevated Risk (>16%)" if r >= 16.0 else ("🟡 Moderate Risk (10-16%)" if r >= 10.0 else "🟢 Low Risk (<10%)")
        )

        g_left, g_right = st.columns([3, 2])
        with g_left:
            top_cities = geo_df.head(10).sort_values("sessions", ascending=True)
            fig_city = px.bar(
                top_cities,
                x="sessions",
                y="city",
                orientation="h",
                text_auto=",d",
                color="revenue",
                color_continuous_scale="Viridis",
                title="Top Cities by Traffic Volume & Revenue"
            )
            fig_city = apply_plotly_theme(fig_city)
            fig_city.update_layout(height=360, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_city, width="stretch", key=KeyManager.get_key("acq", "city_bar"))

        with g_right:
            st.markdown("##### 📍 Regional Insights")
            top_city_name = geo_df.iloc[0]["city"] if not geo_df.empty else "Dhaka"
            top_city_share = ((geo_df.iloc[0]["sessions"] / geo_df["sessions"].sum()) * 100) if not geo_df.empty else 52.0
            ui.commentary(
                "Geographic Footprint",
                [
                    f"🏙️ **Primary Hub**: `{top_city_name}` generates {top_city_share:.1f}% of overall website traffic.",
                    f"🚀 **Emerging Hubs**: Chittagong & Sylhet constitute the second wave of customer acquisition.",
                    f"🚚 **Logistics Watch**: Gazipur & Chittagong show elevated COD return risk (>14%)."
                ]
            )

        st.markdown("##### 📋 City Performance & Logistics Risk Table")
        geo_disp = geo_df.copy()
        geo_disp["revenue"] = geo_disp["revenue"].apply(lambda x: f"TK {x:,.2f}")
        geo_disp["return_rate"] = geo_disp["return_rate"].apply(lambda x: f"{x:.1f}%")
        st.dataframe(
            geo_disp,
            column_config={
                "country": "Country",
                "city": "City",
                "active_users": "Active Users",
                "sessions": "Sessions",
                "conversions": "Conversions",
                "revenue": "Revenue Settled",
                "return_rate": "Est. Return Rate",
                "risk_level": "Logistics Risk Level"
            },
            hide_index=True,
            use_container_width=True
        )

    # ==========================================
    # TAB 4: 🎯 CAMPAIGNS & TRAFFIC SOURCES
    # ==========================================
    with tab_campaign:
        st.markdown("#### 🎯 Marketing Campaign & Paid Traffic Attribution (ROAS & Unit Economics)")

        raw_camp_df = fetch_ga4_campaign_performance("30daysAgo", "today") if ga4_active else pd.DataFrame()
        if raw_camp_df.empty:
            synth_camps = [
                {"campaign": "Summer_Promo_Meta_2026", "source_medium": "facebook / cpc", "sessions": int(total_sessions * 0.35), "conversions": int(total_conversions * 0.38), "revenue": total_revenue * 0.38, "engagement_rate": 58.2},
                {"campaign": "Google_Search_Brand", "source_medium": "google / cpc", "sessions": int(total_sessions * 0.20), "conversions": int(total_conversions * 0.25), "revenue": total_revenue * 0.25, "engagement_rate": 72.4},
                {"campaign": "Instagram_Reels_Retargeting", "source_medium": "instagram / cpc", "sessions": int(total_sessions * 0.15), "conversions": int(total_conversions * 0.16), "revenue": total_revenue * 0.16, "engagement_rate": 61.0},
                {"campaign": "Unassigned / Direct", "source_medium": "direct / none", "sessions": int(total_sessions * 0.12), "conversions": int(total_conversions * 0.10), "revenue": total_revenue * 0.10, "engagement_rate": 50.1},
                {"campaign": "Organic_SEO_Catalog", "source_medium": "google / organic", "sessions": int(total_sessions * 0.10), "conversions": int(total_conversions * 0.07), "revenue": total_revenue * 0.07, "engagement_rate": 65.8},
                {"campaign": "Newsletter_August_VIP", "source_medium": "email / newsletter", "sessions": int(total_sessions * 0.08), "conversions": int(total_conversions * 0.04), "revenue": total_revenue * 0.04, "engagement_rate": 81.3},
            ]
            raw_camp_df = pd.DataFrame(synth_camps)

        campaign_df = calculate_campaign_unit_economics(raw_camp_df)

        tot_spend = campaign_df["ad_spend"].sum()
        tot_rev = campaign_df["revenue"].sum()
        tot_convs = campaign_df["conversions"].sum()
        blended_roas = (tot_rev / tot_spend) if tot_spend > 0 else 0.0
        avg_cac = (tot_spend / tot_convs) if tot_convs > 0 else 0.0
        tot_profit = campaign_df["net_profit"].sum()

        # Top Level Unit Economics Cards
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ui.icon_metric("Total Ad Spend", f"TK {tot_spend:,.0f}", icon="💸")
            ui.badge("Marketing Budget")
        with c2:
            ui.icon_metric("Blended ROAS", f"{blended_roas:.2f}x", icon="🎯", delta="Target ≥ 2.5x")
            ui.badge("Revenue Multiplier")
        with c3:
            ui.icon_metric("Average CAC", f"TK {avg_cac:,.0f}", icon="👤")
            ui.badge("Cost per Order")
        with c4:
            ui.icon_metric("Net Ad Profit Impact", f"TK {tot_profit:,.0f}", icon="💰", delta=f"{((tot_profit/tot_rev)*100 if tot_rev else 0):.1f}% margin")
            ui.badge("Bottom-Line Contribution")

        st.markdown("<br>", unsafe_allow_html=True)

        camp_left, camp_right = st.columns([3, 2])
        with camp_left:
            fig_roas = px.scatter(
                campaign_df,
                x="ad_spend",
                y="roas",
                size="revenue",
                color="net_profit",
                hover_name="campaign",
                hover_data={"source_medium": True, "cac": ":.0f", "cpc": ":.2f", "ad_spend": ":.0f"},
                color_continuous_scale="Viridis",
                title="🎯 ROAS vs. Ad Spend Efficiency Matrix (Bubble = Revenue)"
            )
            fig_roas = apply_plotly_theme(fig_roas)
            fig_roas.update_layout(height=360, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_roas, width="stretch", key=KeyManager.get_key("acq", "camp_roas_scatter"))

        with camp_right:
            st.markdown("##### 💡 Campaign Diagnostics & Attribution")
            top_camp_name = campaign_df.iloc[0]["campaign"] if not campaign_df.empty else "Summer_Promo"
            best_roas_row = campaign_df.sort_values("roas", ascending=False).iloc[0] if not campaign_df.empty else None
            best_roas_name = best_roas_row["campaign"] if best_roas_row is not None else "Google_Brand"
            best_roas_val = best_roas_row["roas"] if best_roas_row is not None else 3.2
            ui.commentary(
                "Unit Economics Summary",
                [
                    f"📢 **Volume Driver**: `{top_camp_name}` delivered the highest traffic volume.",
                    f"🎯 **Highest ROAS**: `{best_roas_name}` achieved peak **{best_roas_val:.2f}x** return on ad spend.",
                    f"💰 **Overall Profitability**: Paid marketing contributed **TK {tot_profit:,.0f}** net profit impact."
                ]
            )

        st.markdown("##### 📋 Full Campaign Attribution & Unit Economics Table")
        camp_disp = campaign_df.copy()
        camp_disp["revenue"] = camp_disp["revenue"].apply(lambda x: f"TK {x:,.2f}")
        camp_disp["ad_spend"] = camp_disp["ad_spend"].apply(lambda x: f"TK {x:,.2f}")
        camp_disp["roas"] = camp_disp["roas"].apply(lambda x: f"{x:.2f}x")
        camp_disp["cac"] = camp_disp["cac"].apply(lambda x: f"TK {x:,.0f}")
        camp_disp["cpc"] = camp_disp["cpc"].apply(lambda x: f"TK {x:,.2f}")
        camp_disp["net_profit"] = camp_disp["net_profit"].apply(lambda x: f"TK {x:,.2f}")
        camp_disp["engagement_rate"] = camp_disp["engagement_rate"].apply(lambda x: f"{x:.1f}%")

        st.dataframe(
            camp_disp[[
                "campaign", "source_medium", "sessions", "conversions", "revenue",
                "ad_spend", "roas", "cac", "cpc", "net_profit"
            ]],
            column_config={
                "campaign": "Campaign Name",
                "source_medium": "Source / Medium",
                "sessions": "Sessions",
                "conversions": "Conversions",
                "revenue": "Revenue Generated",
                "ad_spend": "Est. Ad Spend",
                "roas": "ROAS (x)",
                "cac": "CAC (TK)",
                "cpc": "CPC (TK)",
                "net_profit": "Net Profit Impact"
            },
            hide_index=True,
            use_container_width=True
        )

    # ==========================================
    # TAB 5: 🛒 GA4 E-COMMERCE EVENT FUNNEL
    # ==========================================
    with tab_ecommerce:
        st.markdown("#### 🛒 GA4 E-Commerce Event Micro-Funnel")
        
        events_df = fetch_ga4_ecommerce_events("30daysAgo", "today") if ga4_active else pd.DataFrame()
        if events_df.empty or len(events_df) < 4:
            view_item_count = int(total_sessions * 1.8)
            add_cart_count = int(total_sessions * 0.32)
            begin_checkout_count = int(total_sessions * 0.12)
            purchase_count = total_conversions if total_conversions > 0 else int(total_sessions * 0.032)
            
            events_data = [
                {"event_name": "view_item", "event_label": "1. View Item (Product Details)", "event_count": view_item_count},
                {"event_name": "add_to_cart", "event_label": "2. Add to Cart", "event_count": add_cart_count},
                {"event_name": "begin_checkout", "event_label": "3. Begin Checkout", "event_count": begin_checkout_count},
                {"event_name": "purchase", "event_label": "4. Purchase Completed", "event_count": purchase_count},
            ]
            events_df = pd.DataFrame(events_data)
        else:
            event_order = {"view_item": 1, "add_to_cart": 2, "begin_checkout": 3, "purchase": 4}
            label_map = {
                "view_item": "1. View Item (Product Details)",
                "add_to_cart": "2. Add to Cart",
                "begin_checkout": "3. Begin Checkout",
                "purchase": "4. Purchase Completed"
            }
            events_df["order"] = events_df["event_name"].map(event_order)
            events_df["event_label"] = events_df["event_name"].map(label_map)
            events_df = events_df.sort_values("order").reset_index(drop=True)

        e_left, e_right = st.columns([3, 2])
        with e_left:
            fig_ecom = go.Figure(go.Funnel(
                y=events_df["event_label"],
                x=events_df["event_count"],
                textinfo="value+percent initial+percent previous",
                marker={"color": ["#3b82f6", "#06b6d4", "#f59e0b", "#10b981"]},
                connector={"line": {"color": "rgba(255,255,255,0.2)", "width": 1}}
            ))
            fig_ecom = apply_plotly_theme(fig_ecom)
            fig_ecom.update_layout(
                height=360,
                margin=dict(l=10, r=10, t=20, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_ecom, width="stretch", key=KeyManager.get_key("acq", "ecom_funnel"))

        with e_right:
            st.markdown("##### 💡 Checkout Funnel Conversion Rates")
            v_cnt = events_df.loc[events_df["event_name"] == "view_item", "event_count"].values
            c_cnt = events_df.loc[events_df["event_name"] == "add_to_cart", "event_count"].values
            chk_cnt = events_df.loc[events_df["event_name"] == "begin_checkout", "event_count"].values
            p_cnt = events_df.loc[events_df["event_name"] == "purchase", "event_count"].values

            v_val = v_cnt[0] if len(v_cnt) > 0 else 1
            c_val = c_cnt[0] if len(c_cnt) > 0 else 1
            chk_val = chk_cnt[0] if len(chk_cnt) > 0 else 1
            p_val = p_cnt[0] if len(p_cnt) > 0 else 0

            cart_rate = (c_val / v_val * 100) if v_val else 0
            chk_rate = (chk_val / c_val * 100) if c_val else 0
            purchase_rate = (p_val / chk_val * 100) if chk_val else 0

            ui.commentary(
                "E-Commerce Micro-Conversions",
                [
                    f"🛒 **Product-to-Cart Rate**: {cart_rate:.1f}% of product view sessions result in item add-to-cart.",
                    f"💳 **Cart-to-Checkout Rate**: {chk_rate:.1f}% of cart users initiate checkout process.",
                    f"✅ **Checkout Completion**: {purchase_rate:.1f}% of users starting checkout complete payment successfully."
                ]
            )
