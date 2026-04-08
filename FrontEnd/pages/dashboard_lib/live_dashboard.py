import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime, timedelta
import os
import base64
from typing import Tuple, Dict, Any, Optional

# Relative imports based on the library structure
from BackEnd.services.hybrid_data_loader import load_hybrid_data
from FrontEnd.utils.error_handler import log_error
from FrontEnd.components import ui
import sys
# Ensure app_modules is discoverable if root isn't in path
if os.path.dirname(os.path.dirname(os.path.dirname(__file__))) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app_modules.sales_dashboard import render_operational_forecast, render_category_intelligence

def _reset_live_state():
    """Clears all live-session state as specified in architecture."""
    st.session_state.wc_curr_df = None      # Current live dataframe
    st.session_state.wc_prev_df = None      # Previous shift snapshot
    st.session_state.live_sync_time = None   # Last sync timestamp
    st.session_state.wc_view_historical = False
    st.session_state.wc_sync_mode = "Operational Cycle"
    # Also clear navigation if needed
    if "live_nav_mode" in st.session_state:
        st.session_state.live_nav_mode = "Today"

def log_system_event(event_type: str, message: str):
    """Logs system events for persistence/debugging."""
    log_error(message, context=f"LIVE_DASHBOARD_{event_type}")

def render_reset_confirm(label: str, tool_id: str, reset_callback):
    """
    Renders a confirmation-style reset button.
    Architecture: Shows a "Reset?" confirmation dialog.
    """
    reset_key = f"reset_confirm_{tool_id}"
    if f"pending_reset_{tool_id}" not in st.session_state:
        st.session_state[f"pending_reset_{tool_id}"] = False

    if not st.session_state[f"pending_reset_{tool_id}"]:
        if st.button(f"🗑️ Reset {label}", key=f"btn_reset_{tool_id}"):
            st.session_state[f"pending_reset_{tool_id}"] = True
            st.rerun()
    else:
        st.warning(f"Reset {label}? This will clear your current live session view.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Yes, Reset", key=f"btn_confirm_{tool_id}", type="primary"):
                reset_callback()
                st.session_state[f"pending_reset_{tool_id}"] = False
                st.rerun()
        with c2:
            if st.button("❌ Cancel", key=f"btn_cancel_{tool_id}"):
                st.session_state[f"pending_reset_{tool_id}"] = False
                st.rerun()

# Standard columns for operational ledgers
DASHBOARD_SALES_COLUMNS = [
    "order_id", "order_date", "order_total", "customer_key", "customer_name",
    "order_status", "source", "city", "state", "qty", "item_name",
    "item_revenue", "line_total", "item_cost", "price", "sku", "Category", "Coupons"
]

def load_live_source() -> Tuple[pd.DataFrame, str, datetime]:
    """
    Data Loading Pipeline.
    Architecture: load_live_source() -> df_live, source_name, modified_at
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Check if we have it in session state already
    if st.session_state.get("wc_curr_df") is not None:
        return st.session_state.wc_curr_df, "WooCommerce Live (Cached Session)", st.session_state.get("live_sync_time", datetime.now())

    # Fetch fresh live data using hybrid loader
    df = load_hybrid_data(start_date=today_str, end_date=today_str, woocommerce_mode="live")
    
    # Apply Schema Standardization
    from .data_helpers import prune_dataframe
    df = prune_dataframe(df, DASHBOARD_SALES_COLUMNS)
    
    source_name = "WooCommerce REST API"
    modified_at = datetime.now()
    
    # Store in session state
    st.session_state.wc_curr_df = df
    st.session_state.live_sync_time = modified_at
    
    return df, source_name, modified_at

def find_columns(df: pd.DataFrame) -> Dict[str, str]:
    """
    Auto-maps unpredictable source columns to semantic keys using fuzzy matching logic.
    Required: name, cost, qty
    Optional: date, order_id, phone
    """
    mapping = {}
    cols = df.columns.tolist()
    
    # Semantic rules mapping
    rules = {
        "name": ["item_name", "product name", "item", "description", "title", "name"],
        "cost": ["order_total", "item_revenue", "line_total", "total", "amount", "price_bdt", "revenue", "price"],
        "qty": ["qty", "quantity", "units", "count", "items", "amount"],
        "date": ["order_date", "created at", "date", "timestamp", "time", "date_created"],
        "order_id": ["order_id", "order #", "invoice_no", "id", "order id"],
        "phone": ["phone", "customer phone", "mobile", "contact", "billing_phone"],
    }
    
    for key, candidates in rules.items():
        found = False
        # 1. Exact or case-insensitive match
        for c in candidates:
            match = next((col for col in cols if col.lower().strip() == c.lower().strip()), None)
            if not match:
                # 2. Try replacing spaces with underscores
                match = next((col for col in cols if col.lower().strip().replace(" ", "_") == c.lower().strip().replace(" ", "_")), None)
            if match:
                mapping[key] = match
                found = True
                break
        
        # 3. Last resort fallback (only for criticals)
        if not found and key in ["name", "cost", "qty"]:
            # If any typical e-commerce column is found by keyword search
            kw_match = next((col for col in cols if key in col.lower()), None)
            if kw_match:
                mapping[key] = kw_match
                found = True
            elif key == "cost":
                # Special case for cost if still not found
                for fall in ["amount", "total", "revenue", "price"]:
                    m = next((c for c in cols if fall in c.lower()), None)
                    if m: 
                        mapping[key] = m
                        found = True
                        break
                
    return mapping

def process_data(df: pd.DataFrame, mapping: Dict[str, str], is_historical: bool = False) -> Dict[str, Any]:
    """
    Processes the raw dataframe into visualization objects with operational cycle logic.
    Returns: drill, summ, top, timeframe, basket, win_start, win_end
    """
    if df.empty:
        return {
            "drill": pd.DataFrame(), 
            "summ": {"revenue": 0, "orders": 0, "avg_order": 0, "total_units": 0, "shipped_count": 0, "pending_backlog": 0, "processing_count": 0}, 
            "top": pd.DataFrame(), 
            "timeframe": pd.DataFrame(), 
            "basket": pd.DataFrame()
        }

    # Column accessors
    n_col = mapping.get("name")
    c_col = mapping.get("cost")
    q_col = mapping.get("qty")
    d_col = mapping.get("date")
    id_col = mapping.get("order_id", "order_id")
    s_col = "order_status" # Status is usually standardized by ensure_sales_schema
    m_col = "shipped_date" # date_modified is usually mapped here
    
    w_df = df.copy()
    
    # Numeric conversion
    w_df[c_col] = pd.to_numeric(w_df[c_col], errors="coerce").fillna(0)
    w_df[q_col] = pd.to_numeric(w_df[q_col], errors="coerce").fillna(0)
    
    # Parse dates
    w_df["_dt_created"] = pd.to_datetime(w_df[d_col], errors="coerce").dt.tz_localize(None)
    w_df["_dt_modified"] = pd.to_datetime(w_df.get(m_col, w_df[d_col]), errors="coerce").dt.tz_localize(None)
    
    # 1. ORCHESTRATE OPERATIONAL WINDOW (5:30 PM Cutoff)
    now = datetime.now()
    cutoff_time = now.replace(hour=17, minute=30, second=0, microsecond=0)
    
    # Default: shift started yesterday 5:30 PM
    slot_start = cutoff_time - timedelta(days=1)
    
    # Weekend special logic (Friday is weekend in BD)
    if now.weekday() == 5: # Saturday
        slot_start = cutoff_time - timedelta(days=2)
        
    # Status flags
    is_shipped_final = w_df[s_col].str.lower().isin(["completed", "shipped", "confirmed", "approved"])
    is_processing = w_df[s_col].str.lower() == "processing"
    is_hold = w_df[s_col].str.lower().isin(["on-hold", "onhold"])
    is_waiting = w_df[s_col].str.lower().isin(["pending", "waiting"])
    
    # Logic: "Shipped Sales" now includes Confirmed/Approved as they are ready for dispatch
    if is_historical:
        # If it's a historical/prev view, don't window it - take everything in df (which is already windowed by the loader)
        df_shipped_today = w_df[is_shipped_final].copy()
        win_label_start = w_df["_dt_modified"].min() if not w_df.empty else slot_start
    else:
        df_shipped_today = w_df[is_shipped_final & (w_df["_dt_modified"] >= slot_start)].copy()
        win_label_start = slot_start
    
    # Logic: Pending/Backlog represents everything on hold or waiting
    df_pending_backlog = w_df[is_hold | is_waiting].copy()
    
    # If it's past 5:30 PM, current "Processing" is technically tomorrow's work
    if now > cutoff_time:
        df_processing = pd.DataFrame()
        # Today's processing becomes tomorrow's pending
        curr_processing = w_df[is_processing].copy()
        df_pending_backlog = pd.concat([df_pending_backlog, curr_processing])
    else:
        df_processing = w_df[is_processing].copy()

    # 2. KPI SUMMARIES
    # --- Sector: Shipped/Finalized (Today) ---
    revenue_ship = df_shipped_today[c_col].sum()
    order_ship = df_shipped_today[id_col].nunique() if id_col in df_shipped_today.columns else len(df_shipped_today)
    units_ship = df_shipped_today[q_col].sum()
    
    # --- Sector: Processing (Live) ---
    revenue_proc = df_processing[c_col].sum() if not df_processing.empty else 0
    order_proc = df_processing[id_col].nunique() if id_col in df_processing.columns else len(df_processing)
    units_proc = df_processing[q_col].sum() if not df_processing.empty else 0
    
    # --- Sector: Pending & Backlog (Queue) ---
    revenue_pb = df_pending_backlog[c_col].sum() if not df_pending_backlog.empty else 0
    order_pb = df_pending_backlog[id_col].nunique() if id_col in df_pending_backlog.columns else len(df_pending_backlog)
    units_pb = df_pending_backlog[q_col].sum() if not df_pending_backlog.empty else 0

    summ = {
        "shipped_revenue": revenue_ship,
        "shipped_orders": order_ship,
        "shipped_units": units_ship,
        "proc_revenue": revenue_proc,
        "proc_orders": order_proc,
        "proc_units": units_proc,
        "pb_revenue": revenue_pb,
        "pb_orders": order_pb,
        "pb_units": units_pb,
        # Legacy/Compatibility keys
        "revenue": revenue_ship,
        "orders": order_ship,
        "shipped_count": order_ship,
        "processing_count": order_proc,
        "pending_backlog": order_pb
    }
    
    # 3. TOP PRODUCTS (within today's shipped)
    top = df_shipped_today.groupby(n_col).agg({
        q_col: "sum",
        c_col: "sum"
    }).sort_values(c_col, ascending=False).reset_index().head(10)
    top.columns = ["Product", "Qty", "Revenue"]
    
    # 4. HOURLY VELOCITY (shipped today)
    timeframe = pd.DataFrame()
    if not df_shipped_today.empty:
        df_shipped_today["hour"] = df_shipped_today["_dt_modified"].dt.hour
        timeframe = df_shipped_today.groupby("hour").agg({c_col: "sum", q_col: "sum"}).reindex(range(24), fill_value=0).reset_index()
        timeframe.columns = ["Hour", "Revenue", "Volume"]

    # 5. DRILL DOWN 
    # Standard operational columns should always be included in drill-down
    ledger_cols = ["order_id", "order_date", "customer_name", "order_total", "order_status", "city"]
    available_drill = [c for c in ledger_cols if c in w_df.columns]
    
    # Add mapping columns if they weren't in ledger_cols
    for mapping_col in [n_col, q_col, c_col, s_col, m_col]:
        if mapping_col and mapping_col in w_df.columns and mapping_col not in available_drill:
            available_drill.append(mapping_col)
            
    drill = w_df[available_drill].copy()
    
    return {
        "drill": drill,
        "summ": summ,
        "top": top,
        "timeframe": timeframe,
        "basket": pd.DataFrame(),
        "win_start": win_label_start,
        "win_end": cutoff_time
    }

def render_dashboard_output(data_bundle: Dict[str, Any]):
    """Final visual rendering suite with operational slot counters."""
    summ = data_bundle["summ"]
    top = data_bundle["top"]
    timeframe = data_bundle["timeframe"]
    drill = data_bundle["drill"]
    win_start = data_bundle.get("win_start", datetime.now())

    # Fetch previous day data for the comparative card
    prev_revenue = 0
    prev_orders = 0
    prev_units = 0
    df_prev_raw = pd.DataFrame()
    if "dashboard_data" in st.session_state:
        # Important: Use raw but filter to "Finalized" for the Previous card
        # This represents the shift that ended.
        df_prev_raw = st.session_state.dashboard_data.get("prev_sales", pd.DataFrame())
    
    if not df_prev_raw.empty:
        # Filter to confirmed/shipped/completed for the comparative benchmark
        valid = ["completed", "shipped", "confirmed", "approved"]
        df_prev_final = df_prev_raw[df_prev_raw["order_status"].str.lower().isin(valid)].copy()
        
        from .data_helpers import sum_order_level_revenue
        prev_revenue = sum_order_level_revenue(df_prev_final)
        prev_orders = df_prev_final["order_id"].nunique() if "order_id" in df_prev_final.columns else 0
        prev_units = df_prev_final["qty"].sum() if "qty" in df_prev_final.columns else 0

    now = datetime.now()
    cutoff_time = now.replace(hour=17, minute=30, second=0, microsecond=0)
    morning_start = now.replace(hour=9, minute=0, second=0, microsecond=0)

    # MAIN KPI ROW (Operational Cycle)
    st.markdown(f"**⚡ Active Window: {win_start.strftime('%b %d, %I:%M %p')} to Today 5:30 PM**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Previous Day Performance
        ui.operational_card(
            title="Previous Day Performance",
            order_count=prev_orders,
            item_count=int(prev_units),
            revenue=prev_revenue,
            icon="📅",
            delta_text=f"Last Shift Finalized",
            item_label="Items Shipped"
        )

    with col2:
        # Todays Shipped Sales
        ui.operational_card(
            title="Todays Shipped Sales",
            order_count=summ["shipped_orders"],
            item_count=int(summ["shipped_units"]),
            revenue=summ["shipped_revenue"],
            icon="🚢",
            delta_text=f"{summ['shipped_orders']} orders (Inc. Confirmed)",
            delta_val=summ['shipped_orders'],
            item_label="Items Sold"
        )

    with col3:
        # Merged Operational Queue based on Time
        # Logic: 9:00 AM to 5:30 PM -> Processing View
        # Logic: 5:30 PM to 9:00 AM -> Backlog View
        is_processing_hours = (now >= morning_start and now <= cutoff_time)
        
        if is_processing_hours:
            target_title = "Operational Hub: Processing"
            target_icon = "⚡"
            o_count = summ["proc_orders"]
            i_count = int(summ["proc_units"])
            r_count = summ["proc_revenue"]
            d_text = f"{summ['pb_orders']} in Hold/Waiting" if summ["pb_orders"] > 0 else ""
            d_val = summ['pb_orders']
            i_label = "item to be sold"
        else:
            target_title = "Operational Hub: Hold/Waiting"
            target_icon = "📥"
            o_count = summ["pb_orders"]
            i_count = int(summ["pb_units"])
            r_count = summ["pb_revenue"]
            # Even in backlog view, we can show if there's any stray processing leftover
            d_text = f"{summ['proc_orders']} left in Processing" if summ["proc_orders"] > 0 else ""
            d_val = 0
            i_label = "total units waiting"

        ui.operational_card(
            title=target_title,
            order_count=o_count,
            item_count=i_count,
            revenue=r_count,
            icon=target_icon,
            delta_text=d_text,
            delta_val=d_val,
            item_label=i_label
        )

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Visualization Suite
    v1, v2 = st.columns([2, 1])
    with v1:
        st.markdown("#### 🕒 Sales Velocity (Current Cycle)")
        if not timeframe.empty and timeframe["Revenue"].sum() > 0:
            fig = px.area(timeframe, x="Hour", y="Revenue", color_discrete_sequence=['#4F46E5'], template="plotly_white")
            fig.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Searching for activity within this operational window...")

    with v2:
        st.markdown("#### 🥇 Leaderboard")
        if not top.empty:
            st.dataframe(top, use_container_width=True, hide_index=True)
        else:
            st.caption("No leaders identified in this cycle.")

    # Data Ledger
    with st.expander("🔍 Operational Ledger (Items Feed)", expanded=False):
        st.dataframe(drill, use_container_width=True, hide_index=True)

def render_live_tab():
    """Main terminal logic for the Live Dashboard."""
    
    # 1. Header & Branding Section
    logo_src = "https://logo.clearbit.com/deencommerce.com"
    try:
        logo_path = os.path.join("assets", "deen_logo.jpg")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            logo_src = f"data:image/png;base64,{b64}"
    except Exception: pass

    header_html = f"""
    <div style="display: flex; justify-content: space-between; align-items: center; background: #ffffff; padding: 1.2rem; border-radius: 12px; border: 1px solid #edf2f7; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 2rem;">
        <div style="display: flex; align-items: center;">
            <img src="{logo_src}" style="height: 48px; border-radius: 4px; margin-right: 1.2rem;" onerror="this.style.display='none'">
            <div>
                <div style="font-size: 0.85rem; color: #718096; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;">Operational Live Terminal</div>
                <div style="font-size: 1.4rem; font-weight: 800; color: #1a202c; line-height: 1.2;">DEEN Commerce Ltd.</div>
            </div>
        </div>
        <div style="text-align: right;">
            <div id="dynamic-clock-live" style="font-family: 'JetBrains Mono', monospace; font-size: 1.3rem; font-weight: 800; color: #4F46E5;">
                {datetime.now().strftime('%I:%M:%S %p')}
            </div>
            <div style="font-size: 0.85rem; color: #718096;">{datetime.now().strftime('%A, %B %d, %Y')}</div>
        </div>
    </div>
    <script>
        function updateClock() {{
            const clockEl = document.getElementById('dynamic-clock-live');
            if (clockEl) {{
                const now = new Date();
                clockEl.innerText = now.toLocaleTimeString('en-US', {{ hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }});
            }}
        }}
        setInterval(updateClock, 1000);
    </script>
    """
    st.markdown(header_html, unsafe_allow_html=True)

    # 2. Controls & Context Row
    ctrl_c1, ctrl_c2 = st.columns([4, 1])
    
    with ctrl_c1:
        last_sync = st.session_state.get("live_sync_time")
        if last_sync:
            diff_m = int((datetime.now() - last_sync).total_seconds() / 60)
            st.markdown(f'<div style="text-align:left; padding-top:10px;"><span class="badge-blue">📡 Real-Time Stream | Last Synced: {diff_m}m ago</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:left; padding-top:10px;"><span class="badge-gray">📡 Initializing Core Stream...</span></div>', unsafe_allow_html=True)

    with ctrl_c2:
        if st.button("🔄 Sync Live", use_container_width=True, key="btn_manual_sync"):
            st.session_state.wc_curr_df = None # Force reload
            st.rerun()

    # 3. State Forcing & Auto-Refresh
    st.session_state["wc_sync_mode"] = "Operational Cycle"
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=30000, key="live_autorefresh_trigger")
    except ImportError: pass

    # 4. Logic Execution
    try:
        # Resolve DataFrame based on mode (Logic is handled inside process_data)
        df_raw, source, updated = load_live_source()
        
        # Mapping & Processing
        mapping = find_columns(df_raw)
        
        # Validation
        required = ["name", "cost", "qty"]
        missing = [m for m in required if m not in mapping]
        if missing:
            st.error(f"Mapping Failure: Missing {', '.join(missing)}")
            st.info("The live data source schema has changed. Please contact system admin.")
            return

        results = process_data(df_raw, mapping, is_historical=False)
        
        # 1. TOP-LEVEL KPIs
        render_dashboard_output(results)
        
        # 1.1 Predictive Projections (ML)
        st.divider()
        forecast_source = st.session_state.get("dashboard_data", {}).get("sales_exec", df_raw)
        
        c1, c2 = st.columns([1, 1.2])
        with c1:
            render_category_intelligence(df_raw)
        with c2:
            render_operational_forecast(forecast_source)
        st.divider()
        
        # 2. UNIFIED OPERATIONS LEDGER
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Section A: Today's Active Shift
        st.markdown("### 🚀 Today's Active Shift Ledger")
        st.dataframe(results["drill"][["order_id", "order_date", "customer_name", "order_total", "order_status", "city"]], 
                     use_container_width=True, hide_index=True)
        
        # Section B: Pending & Backlog Queue
        is_hold = df_raw["order_status"].str.lower().isin(["on-hold", "onhold"])
        is_waiting = df_raw["order_status"].str.lower().isin(["pending", "waiting"])
        cutoff_time = datetime.now().replace(hour=17, minute=30, second=0, microsecond=0)
        
        if datetime.now() > cutoff_time:
            is_proc = df_raw["order_status"].str.lower() == "processing"
            df_pb = df_raw[is_hold | is_waiting | is_proc].copy()
        else:
            df_pb = df_raw[is_hold | is_waiting].copy()
        
        with st.expander(f"📥 Hold/Waiting Ledger ({len(df_pb)} orders)", expanded=False):
            if df_pb.empty:
                st.success("🎉 No orders in Hold/Waiting!")
            else:
                st.dataframe(df_pb[["order_id", "order_date", "customer_name", "order_total", "order_status", "city"]], 
                             use_container_width=True, hide_index=True)

        # Section C: Previous Shift Finalized
        df_prev_raw = st.session_state.dashboard_data.get("prev_sales", pd.DataFrame())
        with st.expander(f"📅 Previous Shift Finalized Ledger", expanded=False):
            if df_prev_raw.empty:
                st.info("No comparative shift data in session.")
            else:
                mapping_prev = find_columns(df_prev_raw)
                if mapping_prev:
                    res_prev = process_data(df_prev_raw, mapping_prev, is_historical=True)
                    st.dataframe(res_prev["drill"][["order_id", "order_date", "customer_name", "order_total", "order_status", "city"]], 
                                 use_container_width=True, hide_index=True)
                else:
                    st.warning("Previous schema mismatch.")

    except Exception as e:
        log_system_event("RUNTIME_ERROR", str(e))
        st.error(f"Live Terminal Exception: {str(e)}")

    # 5. Footer / Reset
    st.divider()
    render_reset_confirm("Live Session", "live_terminal", _reset_live_state)

if __name__ == "__main__":
    render_live_tab()
