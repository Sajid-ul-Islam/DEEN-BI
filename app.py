import os
import traceback
from datetime import datetime, timedelta
import pandas as pd

import streamlit as st

from FrontEnd.utils.config import APP_TITLE, APP_DATA_START_DATE

# MUST BE THE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None
from FrontEnd.utils.error_handler import ERROR_LOG_FILE, get_logs, log_error
from FrontEnd.utils.state import init_state
from FrontEnd.components import ui
from BackEnd.core.dependencies import render_dependency_alerts


# ── Numbered dataframe rows (1-based index for readability) ──────────────────
# NOTE: We keep this patch because Streamlit has no native 1-based row numbering.
# The plotly monkey-patch has been removed — transparency is now handled via
# apply_plotly_theme() in charts.py and the global CSS paper_bgcolor rule.
_original_dataframe = st.dataframe


def _numbered_dataframe(data, *args, **kwargs):
    try:
        if isinstance(data, (pd.DataFrame, pd.Series)):
            # Only alter index if it is a default RangeIndex to preserve
            # Time-Series / Grouped Data integrity
            if isinstance(data.index, pd.RangeIndex):
                copied = data.copy()
                if len(copied) > 0:
                    copied.index = pd.RangeIndex(start=1, stop=len(copied) + 1)
                return _original_dataframe(copied, *args, **kwargs)
    except Exception:
        pass
    return _original_dataframe(data, *args, **kwargs)


st.dataframe = _numbered_dataframe


def _clear_error_logs():
    if os.path.exists(ERROR_LOG_FILE):
        os.remove(ERROR_LOG_FILE)


@st.dialog("⚠️ Confirm System Reset")
def _confirm_reset():
    st.write("Are you sure you want to completely reset the system? This will clear all cached data and session state.")
    if st.button("Yes, Reset System", type="primary", use_container_width=True, icon="🚨"):
        from FrontEnd.utils.state import STATE_FILE
        if os.path.exists(STATE_FILE):
            try:
                os.remove(STATE_FILE)
            except Exception:
                pass
        st.session_state.clear()
        st.rerun()
    if st.button("Cancel", use_container_width=True, icon="❌"):
        st.rerun()


def _render_workspace_sidebar():
    with st.sidebar:
        ui.sidebar_branding()

        # ── Time Window ──────────────────────────────────────────────────────
        if "time_window" not in st.session_state:
            st.session_state.time_window = "Last Month"

        def _on_time_window_change():
            st.session_state.pop("refund_alert_shown", None)
            from FrontEnd.utils.state import garbage_collect_session_state
            garbage_collect_session_state(clear_data=True)

        st.markdown('<div class="sidebar-group-label">⏱️ Operational Range</div>', unsafe_allow_html=True)
        st.select_slider(
            "Time Window",
            options=[
                "Last Day", "Last 3 Days", "Last 7 Days", "Last 15 Days", "Last Month",
                "Last 3 Months", "Last Quarter", "Last Half Year", "Last 9 Months", "Last Year", "Custom Date Range",
            ],
            key="time_window",
            label_visibility="collapsed",
            on_change=_on_time_window_change,
        )

        # Smart Shift indicator
        now = datetime.now()
        shift_cutoff = now.replace(hour=17, minute=30, second=0, microsecond=0)
        is_after_cutoff = now >= shift_cutoff
        shift_label = "Night Shift (Post-Cutoff)" if is_after_cutoff else "Day Shift (Processing)"
        st.markdown(
            f'<div style="font-size:0.72rem; color:var(--on-surface-variant); opacity:0.8; '
            f'margin-top:-8px; margin-bottom:12px; padding-left:4px;">🔄 <b>{shift_label}</b></div>',
            unsafe_allow_html=True,
        )

        if st.session_state.get("time_window") == "Custom Date Range":
            col1, col2 = st.columns(2)
            with col1:
                st.date_input(
                    "Start Date",
                    value=datetime.now().date() - timedelta(days=30),
                    min_value=APP_DATA_START_DATE,
                    max_value=datetime.now().date(),
                    key="wc_sync_start_date",
                    on_change=_on_time_window_change,
                )
            with col2:
                st.date_input(
                    "End Date",
                    value=datetime.now().date(),
                    min_value=APP_DATA_START_DATE,
                    max_value=datetime.now().date(),
                    key="wc_sync_end_date",
                    on_change=_on_time_window_change,
                )

        st.divider()

        # ── Navigation ───────────────────────────────────────────────────────
        if "active_section" not in st.session_state:
            st.session_state.active_section = "💎 Sales Overview"

        # Migration guards for renamed tabs
        if st.session_state.active_section == "🚀 Data Pilot":
            st.session_state.active_section = "🛡️ Strategic Command"
        if st.session_state.active_section == "🔄 Returns & Net Sales":
            st.session_state.active_section = "🔄 Returns Insights"
        if st.session_state.get("active_section") in ["📊 Traffic & Acquisition", "Traffic & Acquisition"]:
            st.session_state.active_section = "📊 Traffic Insights"
        if st.session_state.get("active_section") in ["📥 Sales Data Ingestion", "Sales Data Ingestion"]:
            st.session_state.active_section = "📥 Sales Insights"

        def _update_section(new_section):
            if st.session_state.get("active_section") != new_section:
                st.session_state.active_section = new_section
                from FrontEnd.utils.state import garbage_collect_session_state
                garbage_collect_session_state(clear_data=False)

        def page_sales_overview(): _update_section("💎 Sales Overview")
        def page_sales_insights(): _update_section("📥 Sales Insights")
        def page_stock_insight(): _update_section("📦 Stock Insight")
        def page_customer_insight(): _update_section("👥 Customer Insight")
        def page_returns_insights(): _update_section("🔄 Returns Insights")
        def page_traffic_insights(): _update_section("📊 Traffic Insights")
        def page_strategic_command(): _update_section("🛡️ Strategic Command")

        pg = st.navigation({
            "⚡ Navigation Hub": [
                st.Page(page_sales_overview, title="Sales Overview", icon="💎", default=True, url_path="sales-overview"),
                st.Page(page_sales_insights, title="Sales Insights", icon="📥", url_path="sales-insights"),
                st.Page(page_stock_insight, title="Stock Insight", icon="📦", url_path="stock-insight"),
                st.Page(page_customer_insight, title="Customer Insight", icon="👥", url_path="customer-insight"),
                st.Page(page_returns_insights, title="Returns Insights", icon="🔄", url_path="returns-insights"),
                st.Page(page_traffic_insights, title="Traffic Insights", icon="📊", url_path="traffic-insights"),
                st.Page(page_strategic_command, title="Strategic Command", icon="🛡️", url_path="strategic-command"),
            ]
        })

        st.divider()

        # ── Primary Actions ──────────────────────────────────────────────────
        def _trigger_sync():
            st.session_state["global_sync_request"] = True
            st.session_state.pop("refund_alert_shown", None)
            from FrontEnd.utils.state import garbage_collect_session_state
            garbage_collect_session_state(clear_data=True)

        st.button("Sync Operations", icon="🔄", type="primary", use_container_width=True, on_click=_trigger_sync)

        auto_refresh = st.toggle("Auto-Refresh (15 min)", value=False, key="global_auto_refresh")
        if auto_refresh:
            if st_autorefresh:
                st_autorefresh(interval=15 * 60 * 1000, key="global_refresh")
            else:
                st.warning("Auto-refresh is currently unavailable (missing dependency: streamlit-autorefresh).")

        focus_mode = st.toggle("🎥 Focus Mode (War Room)", value=st.session_state.get("focus_mode", False), key="focus_mode_toggle", help="Hides sidebar and increases contrast for large screens")
        if focus_mode != st.session_state.get("focus_mode", False):
            st.session_state.focus_mode = focus_mode
            st.rerun()

        ui.render_theme_selector()

        st.divider()

        # ── Merged System Heartbeat ──────────────────────────────────────────
        st.markdown('<div class="sidebar-group-label">⚙️ Workspace Status</div>', unsafe_allow_html=True)

        sync_time = "Just now"
        if st.session_state.get("live_sync_time"):
            diff = datetime.now() - st.session_state.live_sync_time
            mins = int(diff.total_seconds() / 60)
            sync_time = f"{mins}m ago" if mins > 0 else "Just now"

        from FrontEnd.utils.config import DATA_SYNC_MODE
        mode_label = "Direct" if DATA_SYNC_MODE == "direct" else "Hybrid (BG)"

        st.markdown(
            f"""
            <div class="heartbeat-card">
                <div class="pulse-text">
                    <div class="heartbeat-dot"></div>
                    Operational Cell: Active
                </div>
                <div style="font-size:0.78rem; color:var(--on-surface-variant); margin-top:8px; line-height:1.6;">
                    <b>Last Sync:</b> {sync_time} &nbsp;·&nbsp; <b>Mode:</b> {mode_label}
                </div>
                <div style="margin-top:8px;">
                    <a href="https://deen-ops.streamlit.app/" target="_blank"
                       style="text-decoration:none; color:var(--primary); font-size:0.78rem; font-weight:600;">
                        🔗 DEEN OPS Terminal
                    </a>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Anomaly Toast (fires once per window) ────────────────────────────
        if "dashboard_data" in st.session_state:
            df_curr = st.session_state.dashboard_data.get("sales", pd.DataFrame())
            if not df_curr.empty and "order_status" in df_curr.columns:
                refund_count = len(df_curr[df_curr["order_status"].astype(str).str.lower() == "refunded"])
                if refund_count > 5 and not st.session_state.get("refund_alert_shown", False):
                    st.toast("🚨 Unusual refund activity detected in the current window!", icon="⚠️")
                    st.session_state["refund_alert_shown"] = True

        st.divider()

        # ── Exports (collapsed by default) ───────────────────────────────────
        with st.popover("📤 Exports & Reports", use_container_width=True):
            if "dashboard_data" in st.session_state:
                st.markdown("**🔌 Power BI Connector**")
                st.caption("Generates a Star Schema (Facts & Dimensions) for DAX modeling.")

                if "pbi_export_bytes" not in st.session_state:
                    if st.button("Generate Power BI Matrix", use_container_width=True):
                        with st.spinner("Extracting Facts & Dimensions..."):
                            from BackEnd.services.powerbi_export import build_star_schema
                            returns_df_pbi = st.session_state.get("returns_data", None)
                            excel_bytes, _ = build_star_schema(st.session_state.dashboard_data, returns_df=returns_df_pbi)
                            st.session_state.pbi_export_bytes = excel_bytes
                            st.rerun()
                else:
                    st.download_button(
                        label="📥 Download Star Schema (.xlsx)",
                        data=st.session_state.pbi_export_bytes,
                        file_name=f"deen_powerbi_schema_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary",
                    )

                    def _clear_pbi_cache():
                        st.session_state.pop("pbi_export_bytes", None)
                        from FrontEnd.utils.state import garbage_collect_session_state
                        garbage_collect_session_state(clear_data=False)

                    st.button("Clear Schema Cache", icon="🔄", use_container_width=True, on_click=_clear_pbi_cache)

                st.divider()
                sales_export_df = st.session_state.dashboard_data.get("sales", pd.DataFrame())
                csv = sales_export_df.to_csv(index=False)
                st.download_button(
                    "📥 Raw Dashboard Export (CSV)",
                    csv,
                    "deen_analysis_export.csv",
                    "text/csv",
                    use_container_width=True,
                    disabled=sales_export_df.empty,
                )
            else:
                st.caption("Load dashboard data to enable exports.")

        # ── Admin / System Utils (low-frequency, collapsed) ──────────────────
        with st.popover("🛠️ System Admin", use_container_width=True):
            st.caption("Low-frequency system operations. Use with care.")

            if st.button("Clear Embedding Cache", icon="🧹", use_container_width=True, help="Free up memory and refresh the AI context"):
                from pathlib import Path
                cache_file = Path("BackEnd/cache/embedding_cache.parquet")
                try:
                    if cache_file.exists():
                        cache_file.unlink()
                except Exception:
                    pass
                st.session_state.pop("embedding_cache", None)
                st.toast("Embedding cache cleared!", icon="🧹")

            _render_rag_file_manager()
            _render_pilot_knowledge_manager()
            _render_system_logs()

            st.markdown("---")
            st.markdown("**⚠️ Danger Zone**")
            if st.button("Full System Reset", use_container_width=True, type="secondary", icon="🧨"):
                _confirm_reset()
                
        return pg


def _render_system_logs():
    """Renders system logs inside an expander. Must be called from within the sidebar context."""
    with st.expander("📋 System Logs", expanded=False):
        logs = get_logs()
        if not logs:
            st.info("No system events logged.")
            return
        for log in reversed(logs[-8:]):
            st.caption(f"**{log.get('timestamp')}** | {log.get('context')}")
            st.text(log.get("error"))
            st.divider()
        if st.button("Clear logs", use_container_width=True):
            _clear_error_logs()
            st.rerun()


def _render_rag_file_manager():
    """Renders a file uploader to add documents to the RAG knowledge base."""
    with st.expander("📚 RAG Knowledge Ingestion", expanded=False):
        st.caption("Upload CSV or Excel files to train the Data Pilot on custom datasets.")
        uploaded_files = st.file_uploader(
            "Upload knowledge files", 
            type=["csv", "xlsx", "xls"], 
            accept_multiple_files=True, 
            key="rag_knowledge_uploader",
            label_visibility="collapsed"
        )
        
        if st.button("🚀 Ingest Files", use_container_width=True, disabled=not uploaded_files):
            from pathlib import Path
            knowledge_dir = Path("BackEnd/data/knowledge")
            knowledge_dir.mkdir(parents=True, exist_ok=True)
            
            saved_count = 0
            for uploaded_file in uploaded_files:
                target_path = knowledge_dir / uploaded_file.name
                with open(target_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                saved_count += 1
            
            if saved_count > 0:
                from BackEnd.services.rag_engine import RAGAgent
                agent = RAGAgent()
                with st.spinner(f"Ingesting {saved_count} files into vector store..."):
                    agent.ingest_directory()
                st.toast(f"Successfully ingested {saved_count} files!", icon="✅")


def _render_pilot_knowledge_manager():
    """Renders the AI knowledge base editor. Must be called from within the sidebar context."""
    with st.expander("🧠 AI Knowledge Base", expanded=False):
        from pathlib import Path
        knowledge_file = Path("BackEnd/data/pilot_knowledge.txt")
        current_kb = ""
        if knowledge_file.exists():
            try:
                with open(knowledge_file, "r", encoding="utf-8") as f:
                    current_kb = f.read()
            except Exception:
                pass
        st.caption("Edit the custom rules learned by the Data Pilot.")
        new_kb = st.text_area("Pilot Memory", value=current_kb, height=150, label_visibility="collapsed")
        if st.button("💾 Save Rules", use_container_width=True):
            try:
                knowledge_file.parent.mkdir(parents=True, exist_ok=True)
                with open(knowledge_file, "w", encoding="utf-8") as f:
                    f.write(new_kb)
                if "llm_response_cache" in st.session_state:
                    st.session_state.llm_response_cache.clear()
                st.toast("Knowledge base updated!", icon="✅")
            except Exception as e:
                st.error(f"Failed to save: {e}")


def _render_primary_navigation():
    try:
        import FrontEnd.pages.dashboard as dashboard
        
        # Dynamically find the correct render function to prevent ImportErrors
        if hasattr(dashboard, 'render_dashboard_tab'):
            dashboard.render_dashboard_tab()
        elif hasattr(dashboard, 'render_intelligence_hub_page'):
            dashboard.render_intelligence_hub_page()
        elif hasattr(dashboard, 'render_dashboard'):
            dashboard.render_dashboard()
        elif hasattr(dashboard, 'main'):
            dashboard.main()
        elif hasattr(dashboard, 'render'):
            dashboard.render()
        else:
            st.warning("Dashboard page loaded, but no standard render function was found (`render_dashboard_tab`, `main`, etc.).")
            
    except Exception as e:
        if "weakref" in str(e):
            log_error(e, context="Dashboard Render (weakref)")
            st.error("A critical error occurred while rendering the dashboard, likely due to a data caching issue.")
            st.warning("This is often a temporary issue related to expiring data references.")
            if st.button("Clear Cache and Rerun", icon="🚨", type="primary"):
                st.session_state.clear()
                st.rerun()
            st.code(f"Error details: {e}\n\nTraceback:\n{traceback.format_exc()}")
        else:
            st.error(f"Failed to load dashboard: {e}")

def _render_global_chat():
    """Renders a full-width AI Data Pilot chat expander at the bottom of the main screen."""
    dashboard_data = st.session_state.get("dashboard_data")
    data_ready = dashboard_data and not dashboard_data.get("sales", pd.DataFrame()).empty
    
    st.markdown("<br><br>", unsafe_allow_html=True)

    nudge_html = ""
    if data_ready:
        sales_df = dashboard_data.get("sales", pd.DataFrame())
        returns_df = st.session_state.get("returns_data", pd.DataFrame())
        
        # Simple fast nudge check
        anomalies_msg = ""
        if "order_status" in sales_df.columns:
            recent_refunds = len(sales_df[sales_df["order_status"].astype(str).str.lower() == "refunded"])
            if recent_refunds > 5:
                anomalies_msg = f"Hey, I noticed a sudden spike with {recent_refunds} refunds recently."
        
        if anomalies_msg:
            nudge_html = f'''
            <div style="display:flex; align-items:center; gap:10px; margin-bottom: 10px;">
                <div style="width: 10px; height: 10px; background-color: #ef4444; border-radius: 50%; box-shadow: 0 0 8px #ef4444; animation: pulse 1.5s infinite;"></div>
                <span style="font-size: 0.9rem; color: #ef4444; font-weight: 600;">Pilot Alert: {anomalies_msg}</span>
            </div>
            <style>@keyframes pulse {{ 0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }} 70% {{ transform: scale(1); box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }} 100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }} }}</style>
            '''

    if nudge_html:
        st.markdown(nudge_html, unsafe_allow_html=True)

    with st.expander("🤖 Open Data Pilot (Global AI Assistant)", expanded=bool(nudge_html)):
        if data_ready:
            sales_df = dashboard_data.get("sales", pd.DataFrame())
            returns_df = st.session_state.get("returns_data", pd.DataFrame())
            stock_df = dashboard_data.get("stock", pd.DataFrame())
            from FrontEnd.components.data_display import render_ai_pilot_chat_ui
            render_ai_pilot_chat_ui(
                sales_df=sales_df,
                returns_df=returns_df,
                stock_df=stock_df,
                key_prefix="global_main_chat",
            )
        else:
            st.info("Load dashboard data first, then return here to chat with the Pilot.")

def _inject_meta_pixel():
    """Injects Meta Pixel base code via HTML injection.
    
    Reads META_PIXEL_ID from environment variables so the ID is never
    hardcoded in source. Set it in Streamlit Cloud > App Settings > Secrets,
    or in a local .env file as: META_PIXEL_ID=123456789012345
    """
    # st.secrets (secrets.toml / Streamlit Cloud) takes priority; os.environ is the local fallback
    try:
        sec = dict(st.secrets) if (hasattr(st, "secrets") and st.secrets) else {}
        meta_sec = sec.get("meta", {}) if isinstance(sec.get("meta"), dict) else {}
        pixel_id = (
            sec.get("META_PIXEL_ID")
            or meta_sec.get("pixel_id")
            or meta_sec.get("META_PIXEL_ID")
            or os.environ.get("META_PIXEL_ID", "")
        )
    except Exception:
        pixel_id = os.environ.get("META_PIXEL_ID", "")
    if not pixel_id:
        return  # Skip silently if not configured

    st.markdown(
        f"""
        <script>
        !function(f,b,e,v,n,t,s)
        {{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
        n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
        if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
        n.queue=[];t=b.createElement(e);t.async=!0;
        t.src=v;s=b.getElementsByTagName(e)[0];
        s.parentNode.insertBefore(t,s)}}(window, document,'script',
        'https://connect.facebook.net/en_US/fbevents.js');
        fbq('init', '{pixel_id}');
        fbq('track', 'PageView');
        </script>
        <noscript>
          <img height="1" width="1" style="display:none"
               src="https://www.facebook.com/tr?id={pixel_id}&ev=PageView&noscript=1"/>
        </noscript>
        """,
        unsafe_allow_html=True,
    )


def run_app():
    init_state()
    ui.setup_theme()
    _inject_meta_pixel()
    render_dependency_alerts()
    pg = _render_workspace_sidebar()
    pg.run()
    ui.page_header()
    _render_primary_navigation()
    
    from FrontEnd.components.command_palette import inject_command_palette_listener
    inject_command_palette_listener()
    
    _render_global_chat()
    ui.page_footer()

    if st.session_state.get("focus_mode", False):
        st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: none !important; }
            html, body, [class*="css"] { font-size: 115% !important; }
            .stApp { background-color: #050505 !important; color: #ffffff !important; }
            [data-testid="stMetricContainer"], .metric-card, .bi-hero, .hub-card { 
                background: #111111 !important; 
                border-color: #333333 !important; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.5) !important;
            }
        </style>
        """, unsafe_allow_html=True)


try:
    run_app()
except Exception as exc:
    log_error(exc, context="App Bootstrap")
    st.error("Application failed to render. Check 'More Tools -> System Logs' for details.")
    st.code(str(exc))
