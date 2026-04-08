import os
import datetime

import streamlit as st

from FrontEnd.utils.config import APP_TITLE
from FrontEnd.utils.error_handler import ERROR_LOG_FILE, get_logs, log_error
from FrontEnd.utils.state import init_state, save_state
from FrontEnd.components import ui


_original_dataframe = st.dataframe


def _numbered_dataframe(data, *args, **kwargs):
    try:
        import pandas as pd

        if isinstance(data, pd.DataFrame) or isinstance(data, pd.Series):
            copied = data.copy()
            if len(copied) > 0:
                copied.index = range(1, len(copied) + 1)
            return _original_dataframe(copied, *args, **kwargs)
    except Exception:
        pass
    return _original_dataframe(data, *args, **kwargs)


st.dataframe = _numbered_dataframe

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="AP",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _clear_error_logs():
    if os.path.exists(ERROR_LOG_FILE):
        os.remove(ERROR_LOG_FILE)


def _render_workspace_sidebar():
    with st.sidebar:
        ui.sidebar_branding()
        
        if "time_window" not in st.session_state:
            st.session_state.time_window = "Last 7 Days"

        st.select_slider(
            "Time Window",
            options=[
                "Yesterday & Today", 
                "Last 3 Days", 
                "Last 7 Days", 
                "Last Month", 
                "MTD",
                "Last 3 Months", 
                "Last Quarter", 
                "Last Half Year", 
                "YTD",
                "Last Year",
                "Custom Date Range"
            ],
            key="time_window"
        )
        
        if st.session_state.get("time_window") == "Custom Date Range":
            st.date_input(
                "Select Date Range",
                value=(datetime.date.today() - datetime.timedelta(days=7), datetime.date.today()),
                min_value=datetime.date(2022, 8, 1),
                max_value=datetime.date.today(),
                key="custom_timestamp_range"
            )

        st.divider()

        # 2. Executive Dashboard Navigation
        st.session_state.active_section = st.radio(
            "Executive Dashboard",
            [
                "💎 Market Overview",
                "🚢 Operational Live",
                "👥 Customer Behavior",
                "🔍 Deep-Dive Clusters",
                "📦 Inventory Health",
                "🛡️ Data Trust"
            ],
            index=0
        )
        st.markdown("[🔗 Open OPS BI Terminal](https://deen-ops.streamlit.app/)")

        st.divider()

        # 2. Global Sync Trigger
        if st.button("🔄 Sync Operations", type="primary", use_container_width=True):
            st.session_state["global_sync_request"] = True
            st.rerun()

        # 3. Status Indicator
        st.markdown("""
            <div style="background:rgba(16, 185, 129, 0.1); border-radius:12px; padding:12px; margin-top:16px;">
                <div style="font-size:0.75rem; color:var(--green); font-weight:700;">LIVE SYSTEM STATUS</div>
                <div style="font-size:0.85rem; color:var(--on-surface);">Connected to WooCommerce</div>
            </div>
        """, unsafe_allow_html=True)

        # 4. Compact Utils
        with st.expander("🛠️ System Utils", expanded=False):
            if st.button("Full System Reset", use_container_width=True):
                from FrontEnd.utils.state import STATE_FILE
                if os.path.exists(STATE_FILE): os.remove(STATE_FILE)
                st.session_state.clear()
                st.rerun()
            
            _render_system_logs()


def _render_system_logs():
    with st.sidebar.expander("System Logs", expanded=False):
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


def _render_primary_navigation():
    from FrontEnd.pages.dashboard import render_intelligence_hub_page
    render_intelligence_hub_page()


def run_app():
    init_state()
    ui.setup_theme()
    _render_workspace_sidebar()
    ui.page_header()
    _render_primary_navigation()
    ui.page_footer()


try:
    run_app()
except Exception as exc:
    log_error(exc, context="App Bootstrap")
    st.error("Application failed to render. Check 'More Tools -> System Logs' for details.")
    st.code(str(exc))
