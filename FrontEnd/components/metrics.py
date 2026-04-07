import pandas as pd
import streamlit as st
from .data_display import _safe_datetime_series















def badge(note: str):
    if not note:
        return
    st.markdown(f'<div class="bi-kpi-note">{note}</div>', unsafe_allow_html=True)




def icon_metric(label: str, value: str, icon: str = "📊", delta: str = "", delta_val: float = 0):
    delta_class = "delta-up" if delta_val >= 0 else "delta-down"
    delta_icon = "↑" if delta_val >= 0 else "↓"
    delta_html = f'<div class="metric-delta {delta_class}">{delta_icon} {delta}</div>' if delta else ""
    
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-icon">{icon}</div>
          <div class="metric-content">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_highlight(label: str, value: str, help_text: str = ""):
    if not label or value is None:
        return
    help_block = f'<div class="bi-highlight-help" style="color:var(--text-muted); font-size:0.9rem; margin-top:4px;">{help_text}</div>' if help_text else ""
    st.markdown(
        f"""
        <div class="stMetricContainer" style="background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:1.5rem; border-left:4px solid var(--primary);">
          <div style="font-size:0.85rem; font-weight:600; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em;">{label}</div>
          <div style="font-size:2.2rem; font-weight:700; color:var(--text-strong); margin-top:8px;">{value}</div>
          {help_block}
        </div>
        """,
        unsafe_allow_html=True,
    )












def date_context(
    requested_start=None,
    requested_end=None,
    loaded_start=None,
    loaded_end=None,
    label: str = "Loaded data",
):
    requested_parts = []
    if requested_start is not None:
        requested_parts.append(f"from {pd.to_datetime(requested_start).strftime('%Y-%m-%d')}")
    if requested_end is not None:
        requested_parts.append(f"to {pd.to_datetime(requested_end).strftime('%Y-%m-%d')}")
    requested_text = " ".join(requested_parts).strip()
    prefix = f"Requested range: {requested_text}" if requested_text else "Requested range: not specified"

    loaded_start_series = _safe_datetime_series(loaded_start)
    loaded_end_series = _safe_datetime_series(loaded_end)
    loaded_start_ts = loaded_start_series.min() if not loaded_start_series.empty and loaded_start_series.notna().any() else pd.NaT
    loaded_end_ts = loaded_end_series.max() if not loaded_end_series.empty and loaded_end_series.notna().any() else pd.NaT
    if pd.notna(loaded_start_ts) and pd.notna(loaded_end_ts):
        st.caption(
            f"{prefix} | {label}: {loaded_start_ts.strftime('%Y-%m-%d %H:%M')} to {loaded_end_ts.strftime('%Y-%m-%d %H:%M')}"
        )
    else:
        st.caption(f"{prefix} | {label}: dates are not available in the current result.")











