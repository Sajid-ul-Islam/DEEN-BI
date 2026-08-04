import os
from datetime import datetime
from typing import Any

import streamlit as st

# ── Themes Palette Registry ──────────────────────────────────────────────────
THEMES: dict[str, dict[str, Any]] = {
    "Indigo Modern": {
        "name": "Indigo Modern",
        "icon": "🔮",
        "description": "Sleek indigo & sapphire corporate aesthetic",
        "primary": "#6366F1",
        "primary_rgb": "99, 102, 241",
        "secondary": "#3B82F6",
        "accent": "#818CF8",
        "gradient_1": "linear-gradient(135deg, #6366F1 0%, #3B82F6 100%)",
        "btn_gradient": "linear-gradient(135deg, #6366F1 0%, #4F46E5 100%)",
        "download_gradient": "linear-gradient(135deg, #10B981 0%, #059669 100%)",
        "download_shadow": "rgba(16, 185, 129, 0.3)",
        "chart_scale": "Plasma",
        "chart_colors": ["#6366F1", "#3B82F6", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6"],
    },
    "Emerald Forest": {
        "name": "Emerald Forest",
        "icon": "🌿",
        "description": "Rich emerald greens & teal eco vibes",
        "primary": "#10B981",
        "primary_rgb": "16, 185, 129",
        "secondary": "#0D9488",
        "accent": "#34D399",
        "gradient_1": "linear-gradient(135deg, #10B981 0%, #059669 100%)",
        "btn_gradient": "linear-gradient(135deg, #10B981 0%, #047857 100%)",
        "download_gradient": "linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)",
        "download_shadow": "rgba(59, 130, 246, 0.3)",
        "chart_scale": "Viridis",
        "chart_colors": ["#10B981", "#059669", "#34D399", "#0EA5E9", "#F59E0B", "#6366F1"],
    },
    "Cyberpunk Neon": {
        "name": "Cyberpunk Neon",
        "icon": "⚡",
        "description": "Electric cyan & hot magenta futuristic theme",
        "primary": "#06B6D4",
        "primary_rgb": "6, 182, 212",
        "secondary": "#EC4899",
        "accent": "#8B5CF6",
        "gradient_1": "linear-gradient(135deg, #06B6D4 0%, #8B5CF6 50%, #EC4899 100%)",
        "btn_gradient": "linear-gradient(135deg, #06B6D4 0%, #8B5CF6 100%)",
        "download_gradient": "linear-gradient(135deg, #EC4899 0%, #BE185D 100%)",
        "download_shadow": "rgba(236, 72, 153, 0.3)",
        "chart_scale": "Turbo",
        "chart_colors": ["#06B6D4", "#EC4899", "#8B5CF6", "#FACC15", "#10B981", "#F97316"],
    },
    "Sunset Amber": {
        "name": "Sunset Amber",
        "icon": "🌅",
        "description": "Warm orange, crimson & violet sunset palette",
        "primary": "#F97316",
        "primary_rgb": "249, 115, 22",
        "secondary": "#E11D48",
        "accent": "#FB923C",
        "gradient_1": "linear-gradient(135deg, #F97316 0%, #E11D48 100%)",
        "btn_gradient": "linear-gradient(135deg, #F97316 0%, #EA580C 100%)",
        "download_gradient": "linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)",
        "download_shadow": "rgba(139, 92, 246, 0.3)",
        "chart_scale": "Sunset",
        "chart_colors": ["#F97316", "#E11D48", "#8B5CF6", "#F59E0B", "#06B6D4", "#10B981"],
    },
    "Oceanic Sapphire": {
        "name": "Oceanic Sapphire",
        "icon": "🌊",
        "description": "Deep royal blue & azure oceanic palette",
        "primary": "#2563EB",
        "primary_rgb": "37, 99, 235",
        "secondary": "#0EA5E9",
        "accent": "#60A5FA",
        "gradient_1": "linear-gradient(135deg, #2563EB 0%, #0284C7 100%)",
        "btn_gradient": "linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)",
        "download_gradient": "linear-gradient(135deg, #F59E0B 0%, #D97706 100%)",
        "download_shadow": "rgba(245, 158, 11, 0.3)",
        "chart_scale": "Blues",
        "chart_colors": ["#2563EB", "#38BDF8", "#F59E0B", "#10B981", "#6366F1", "#EC4899"],
    },
    "Monochrome Slate": {
        "name": "Monochrome Slate",
        "icon": "🖤",
        "description": "Minimalist dark slate & zinc executive look",
        "primary": "#475569",
        "primary_rgb": "71, 85, 105",
        "secondary": "#64748B",
        "accent": "#94A3B8",
        "gradient_1": "linear-gradient(135deg, #475569 0%, #1E293B 100%)",
        "btn_gradient": "linear-gradient(135deg, #475569 0%, #334155 100%)",
        "download_gradient": "linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)",
        "download_shadow": "rgba(14, 165, 233, 0.3)",
        "chart_scale": "Greys",
        "chart_colors": ["#475569", "#64748B", "#94A3B8", "#CBD5E1", "#0EA5E9", "#F59E0B"],
    },
}


def render_theme_selector(key: str = "theme_choice_selector"):
    """Renders a theme picker selectbox for the sidebar."""
    options = list(THEMES.keys())
    current = st.session_state.get("theme_choice", "Indigo Modern")
    if current not in options:
        current = "Indigo Modern"

    selected_name = st.selectbox(
        "🎨 Dashboard Theme",
        options=options,
        index=options.index(current),
        format_func=lambda name: f"{THEMES[name]['icon']} {THEMES[name]['name']}",
        key=key,
        help="Select a color palette for UI elements, buttons, and charts.",
    )

    if selected_name != st.session_state.get("theme_choice"):
        st.session_state["theme_choice"] = selected_name
        from FrontEnd.utils.state import save_state
        save_state()
        st.rerun()


def setup_theme():
    theme_key = st.session_state.get("theme_choice", "Indigo Modern")
    theme = THEMES.get(theme_key, THEMES["Indigo Modern"])

    primary = theme["primary"]
    primary_rgb = theme["primary_rgb"]
    accent = theme["accent"]
    gradient_1 = theme["gradient_1"]
    btn_gradient = theme["btn_gradient"]
    download_gradient = theme["download_gradient"]
    download_shadow = theme["download_shadow"]

    root_css = f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        /* ── Design Tokens (Light Mode) ─────────────────────────────────── */
        :root {{
            --primary: {primary};
            --primary-rgb: {primary_rgb};
            --background: #FFFFFF;
            --surface: #F8FAFC;
            --surface-variant: #F1F5F9;
            --on-surface: #0F172A;
            --on-surface-variant: #64748B;
            --outline: #E2E8F0;
            --green: #10b981;
            --warning: #f59e0b;
            --red: #ef4444;
            --border: #E2E8F0;
            --border-soft: rgba(226, 232, 240, 0.6);
            --text-strong: #0F172A;
            --text-muted: #64748B;
            --card-shadow: 0 4px 15px rgba(0, 0, 0, 0.06);
            --card-shadow-soft: 0 2px 8px rgba(0, 0, 0, 0.05);
            --gradient-1: {gradient_1};
            --btn-gradient: {btn_gradient};
            --download-btn-gradient: {download_gradient};
            --download-btn-shadow: {download_shadow};
            --action-surface: rgba(248, 250, 252, 0.96);
            --accent: {accent};
        }}

        /* ── Design Tokens (Dark Mode) ──────────────────────────────────── */
        @media (prefers-color-scheme: dark) {{
            :root {{
                --primary: {primary};
                --primary-rgb: {primary_rgb};
                --background: #0F172A;
                --surface: #1E293B;
                --surface-variant: #334155;
                --on-surface: #F1F5F9;
                --on-surface-variant: #94A3B8;
                --outline: rgba(148, 163, 184, 0.2);
                --warning: #f59e0b;
                --green: #34d399;
                --red: #f87171;
                --border: rgba(148, 163, 184, 0.2);
                --border-soft: rgba(148, 163, 184, 0.12);
                --text-strong: #F1F5F9;
                --text-muted: #94A3B8;
                --card-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
                --card-shadow-soft: 0 2px 8px rgba(0, 0, 0, 0.25);
                --gradient-1: {gradient_1};
                --btn-gradient: {btn_gradient};
                --download-btn-gradient: {download_gradient};
                --download-btn-shadow: {download_shadow};
                --action-surface: rgba(30, 41, 59, 0.96);
                --accent: {accent};
            }}
        }}
        </style>
    """
    st.markdown(root_css, unsafe_allow_html=True)
    st.markdown(_STATIC_LAYOUT_CSS, unsafe_allow_html=True)


_STATIC_LAYOUT_CSS = """
<style>
/* ── Dialog / Modal Customization ───────────────────────────────── */
[data-testid="stDialog"] {
    border-radius: 24px !important;
    background: var(--surface) !important;
    border: 1px solid rgba(var(--primary-rgb), 0.25) !important;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.3) !important;
    padding: 16px !important;
}

[data-testid="stDialog"] h2 {
    font-weight: 800 !important;
    color: var(--on-surface) !important;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-soft);
}

/* ── Base ───────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

.stApp {
    background-color: var(--background) !important;
    color: var(--on-surface) !important;
}

/* ── Cards & Surfaces ───────────────────────────────────────────── */
[data-testid="stMetricContainer"], .metric-card, .bi-hero, .hub-card {
    background: var(--surface) !important;
    border: 1px solid var(--outline) !important;
    border-radius: 16px !important;
    padding: 1.5rem !important;
    box-shadow: var(--card-shadow) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    backdrop-filter: blur(12px) !important;
    box-sizing: border-box !important;
}

/* Explicit constraints for Metric Cards to keep uniform grid */
[data-testid="stMetricContainer"], .metric-card {
    height: 100% !important;
    min-height: 140px !important;
    display: flex;
    flex-direction: column;
    justify-content: center;
    overflow: hidden !important;
}

/* Hover: border + shadow only on non-interactive containers */
.hub-card:hover {
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1) !important;
    border-color: var(--primary) !important;
}

/* Lift only on metric cards — not commentary/hero blocks */
.metric-icon-card:hover,
.metric-highlight:hover,
.op-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1) !important;
    border-color: var(--primary) !important;
}

[data-testid="stMetricLabel"] {
    font-weight: 600 !important;
    font-size: clamp(0.55rem, 1.2vw, 0.7rem) !important;
    opacity: 0.8;
    color: var(--on-surface-variant) !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
}

/* Metric Highlight Styling */
.metric-highlight {
    padding: 1.25rem !important;
    height: 100% !important;
    min-height: 140px !important;
    border-left: 4px solid var(--primary) !important;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    overflow: hidden !important;
    box-sizing: border-box !important;
}

.metric-highlight-label {
    font-size: clamp(0.55rem, 1.2vw, 0.7rem);
    font-weight: 800;
    color: var(--on-surface-variant);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0;
    opacity: 0.7;
    white-space: normal !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    width: 100%;
}

.metric-highlight-value {
    font-size: clamp(1.5rem, 4vw, 2.5rem);
    font-weight: 800;
    color: var(--on-surface);
    letter-spacing: -0.04em;
    line-height: 1.1;
    margin: 0;
    overflow-wrap: break-word;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    width: 100%;
}

.metric-icon-card {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    height: 100% !important;
    min-height: 140px !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
}

.metric-icon-wrap {
    font-size: 1.4rem;
    background: rgba(var(--primary-rgb), 0.1);
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 10px;
}

[data-testid="stMetricValue"], 
[data-testid="stMetricValue"] > div {
    font-weight: 800 !important;
    font-size: clamp(1.5rem, 4vw, 2.5rem) !important;
    color: var(--on-surface) !important;
    white-space: normal !important;
    word-break: break-word !important;
}

/* Pills and Rounded Buttons (M3 Filled) */
.stButton > button {
    border-radius: 100px !important;
    font-weight: 500 !important;
    letter-spacing: 0.1px !important;
    padding: 0.5rem 1.75rem !important;
    border: none !important;
    background: var(--btn-gradient) !important;
    background-color: var(--primary) !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(var(--primary-rgb), 0.25) !important;
    transition: all 0.3s ease !important;
}

.stButton > button:hover {
    box-shadow: 0 4px 14px rgba(var(--primary-rgb), 0.4) !important;
    opacity: 0.94;
    transform: translateY(-1px) !important;
}

/* Premium Export / Download Button Styling */
div[data-testid="stDownloadButton"] > button {
    background: var(--download-btn-gradient) !important;
    color: white !important;
    border: none !important;
    border-radius: 100px !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    box-shadow: 0 4px 10px var(--download-btn-shadow) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
div[data-testid="stDownloadButton"] > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 14px var(--download-btn-shadow) !important;
    filter: brightness(1.08) !important;
}

/* Premium Input Styling (Selectbox, Multiselect, Text Input) */
div[data-testid="stSelectbox"] > div, 
div[data-testid="stMultiSelect"] > div,
div[data-testid="stTextInput"] > div > div > input {
    background-color: var(--surface) !important;
    border: 1px solid var(--outline) !important;
    border-radius: 8px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    transition: all 0.2s ease-in-out !important;
}
div[data-testid="stSelectbox"] > div:hover, 
div[data-testid="stMultiSelect"] > div:hover,
div[data-testid="stTextInput"] > div > div > input:hover {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(var(--primary-rgb), 0.1) !important;
}
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
    background-color: rgba(var(--primary-rgb), 0.15) !important;
    color: var(--primary) !important;
    border-radius: 6px !important;
}
div[data-testid="stTextInput"] > div > div > input {
    padding-left: 12px !important;
    padding-right: 12px !important;
}

[data-testid="stSidebar"] {
    background-color: var(--surface) !important;
    border-right: 1px solid var(--surface-variant) !important;
}

.main .block-container {
    padding-top: 2rem !important;
    padding-bottom: 5rem !important;
}

/* ── Responsive Breakpoints ─────────────────────────────────────── */
@media (max-width: 1024px) {
    [data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        flex-wrap: wrap !important;
    }
    [data-testid="stColumn"] {
        min-width: calc(33.33% - 1rem) !important;
        flex: 1 1 calc(33.33% - 1rem) !important;
    }
    .hub-card, [data-testid="stMetricContainer"] {
        padding: 0.8rem !important;
        min-height: 80px !important;
        margin-bottom: 8px !important;
    }
    .metric-highlight-value, [data-testid="stMetricValue"] {
        font-size: 1.25rem !important;
    }
    .metric-highlight-label, [data-testid="stMetricLabel"] {
        font-size: 0.6rem !important;
    }
    .metric-icon-card {
        gap: 0.5rem !important;
    }
    .metric-icon-wrap {
        width: 32px !important;
        height: 32px !important;
        font-size: 1.2rem !important;
    }
    .hub-page_footer {
        padding: 10px 0 20px 0 !important;
    }
}

/* Hero and Headers */
.bi-hero {
    background: var(--surface) !important;
    border-radius: 28px !important;
    padding: 2rem !important;
    margin-bottom: 24px !important;
}

/* Tabs (M3 Primary) */
div[data-testid="stTab"] button {
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    border-radius: 100px !important;
    padding: 0.5rem 1rem !important;
}

div[data-testid="stTab"] button[aria-selected="true"] {
    background-color: var(--surface-variant) !important;
    color: var(--primary) !important;
}

/* Live indicator */
.live-indicator {
    display: inline-flex;
    align-items: center;
    font-size: 12px;
    font-weight: 600;
    color: var(--green);
    background: rgba(16, 185, 129, 0.1);
    padding: 4px 10px;
    border-radius: 100px;
    margin-bottom: 20px;
}

.live-dot {
    width: 6px;
    height: 6px;
    background: var(--green);
    border-radius: 50%;
    margin-right: 8px;
    animation: pulse-dot 2s infinite;
}

/* Metric Growth indicators */
.delta-up { color: var(--green) !important; font-weight: 700 !important; font-size: 0.85rem !important; margin-top: 4px; }
.delta-down { color: var(--red) !important; font-weight: 700 !important; font-size: 0.85rem !important; margin-top: 4px; }

/* --- Sidebar Premium Enhancements --- */
.sidebar-group-label {
    font-size: 0.7rem;
    font-weight: 800;
    color: var(--on-surface-variant);
    opacity: 0.6;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin: 24px 0 12px 0;
    padding-left: 4px;
}

.heartbeat-card {
    background: rgba(var(--primary-rgb), 0.05);
    border-left: 3px solid var(--primary);
    border-radius: 12px;
    padding: 12px;
    margin-top: 24px;
}

.pulse-text {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--on-surface);
}

@keyframes heartbeat {
    0% { transform: scale(0.95); opacity: 0.5; }
    50% { transform: scale(1.05); opacity: 1; }
    100% { transform: scale(0.95); opacity: 0.5; }
}

.heartbeat-dot {
    width: 8px;
    height: 8px;
    background: var(--green);
    border-radius: 50%;
    animation: heartbeat 1.5s infinite;
}

@keyframes pulse-dot {
    0% { transform: scale(0.95); opacity: 0.7; }
    50% { transform: scale(1.05); opacity: 1; }
    100% { transform: scale(0.95); opacity: 0.7; }
}

/* Tables and Charts */
[data-testid="stMetricContainer"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1.25rem !important;
}
.hub-card {
    border-radius: 20px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.bi-hero {
    background: linear-gradient(135deg, var(--primary) 0%, #3b82f6 100%) !important;
    color: white !important;
}
.bi-hero::after {
    content: "";
    position: absolute;
    inset: auto -10% -40% auto;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(255,255,255,0.25) 0%, transparent 68%);
    animation: pulse-glow 8s ease-in-out infinite alternate;
}
@keyframes pulse-glow {
    0% { transform: scale(1); opacity: 0.8; }
    100% { transform: scale(1.1); opacity: 1; }
}
.bi-hero-title {
    font-size: 1.8rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin-bottom: 0.5rem;
}
.bi-hero-subtitle {
    max-width: 800px;
    font-size: 1.05rem;
    line-height: 1.6;
    color: rgba(255, 255, 255, 0.9);
    font-weight: 400;
}
.bi-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
    margin-top: 1.2rem;
}
.bi-chip {
    border-radius: 999px;
    padding: 0.36rem 0.72rem;
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.16);
    font-size: 0.75rem;
    color: #f5fbff;
    backdrop-filter: blur(8px);
}
.bi-commentary {
    background: var(--surface);
    border: 1px solid var(--border-soft);
    border-radius: 18px;
    box-shadow: var(--card-shadow-soft);
    padding: 1rem 1.1rem;
    margin-bottom: 1rem;
}
.bi-commentary-label, .bi-audit-title {
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--primary);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 0.8rem;
    display: inline-block;
    background: rgba(var(--primary-rgb), 0.1);
    padding: 4px 10px;
    border-radius: 6px;
}
.bi-commentary ul {
    margin: 0;
    padding-left: 1.2rem;
    color: var(--text-strong);
    font-size: 1rem;
}
.bi-commentary li {
    margin-bottom: 0.6rem;
    line-height: 1.6;
}
.bi-kpi-note {
    margin-top: 0.5rem;
    padding: 0.4rem 0.8rem;
    border-radius: 999px;
    display: inline-block;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--primary);
    background: rgba(var(--primary-rgb), 0.1);
    border: 1px solid rgba(var(--primary-rgb), 0.2);
}
.bi-audit-body {
    color: var(--text-strong);
    line-height: 1.6;
    font-size: 1rem;
}
.bi-highlight-stat {
    background: var(--gradient-1);
    color: #ffffff;
    border-radius: 24px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: var(--card-shadow);
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.2);
}
.bi-highlight-stat::before {
    content: "";
    position: absolute;
    top: 0; right: 0;
    width: 150px; height: 150px;
    background: radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 70%);
    transform: translate(30%, -30%);
}
.bi-highlight-label {
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.8);
    margin-bottom: 0.5rem;
}
.bi-highlight-value {
    font-size: 2.5rem;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -0.04em;
}
.bi-highlight-help {
    margin-top: 0.8rem;
    color: rgba(255, 255, 255, 0.9);
    font-size: 0.95rem;
    line-height: 1.5;
}
[data-testid="stMetricContainer"] {
    border-radius: 20px;
    padding: 1.2rem;
    border-left: 4px solid var(--accent) !important;
}

div[data-testid="stVerticalBlock"]:has(> div[data-testid="stMarkdownContainer"] .hub-action-wrap) {
    position: sticky;
    bottom: 60px;
    padding: 16px;
    border: 1px solid var(--border-soft);
    border-radius: 18px;
    background: var(--action-surface);
    backdrop-filter: blur(16px);
    box-shadow: var(--card-shadow);
    z-index: 100;
    margin-top: 20px;
}

.hub-action-wrap {
    display: none;
}

/* Premium Tab Styling */
div[data-testid="stTab"] button {
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    border: none !important;
    background: transparent !important;
    padding: 14px 24px !important;
    border-radius: 12px !important;
    margin-right: 8px !important;
    border: 1px solid transparent !important;
}
div[data-testid="stTab"] button:hover {
    color: var(--primary) !important;
    background: rgba(var(--primary-rgb), 0.05) !important;
    border-color: rgba(var(--primary-rgb), 0.1) !important;
}
div[data-testid="stTab"] button[aria-selected="true"] {
    color: var(--primary) !important;
    background: var(--surface-variant) !important;
    border: 1px solid rgba(var(--primary-rgb), 0.2) !important;
    box-shadow: 0 4px 12px rgba(var(--primary-rgb), 0.08) !important;
}

/* Responsive Design - Mobile First */
@media (max-width: 768px) {
    .main .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        padding-bottom: 120px !important;
        margin-top: -0.5rem !important;
    }
    .hub-title-row {
        padding: 8px 12px;
        margin-bottom: 8px;
    }
    .hub-title {
        font-size: 1.1rem !important;
        line-height: 1.3;
    }
    .hub-subtitle {
        font-size: 0.75rem !important;
    }
    .hub-card {
        padding: 10px 12px;
        border-radius: 8px;
        margin-bottom: 8px;
    }
    .hub-page_footer {
        padding: 8px 12px;
        font-size: 0.7rem;
        flex-direction: column;
        text-align: center;
        align-items: center;
        justify-content: center;
        display: flex;
        gap: 4px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.1rem !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.7rem !important;
    }
    div[data-testid="stMetricDelta"] {
        font-size: 0.65rem !important;
    }
    div[data-testid="stTab"] button {
        padding: 6px 10px !important;
        font-size: 0.75rem !important;
    }
    .stDataFrame {
        font-size: 0.8rem !important;
    }
    [data-testid="stTable"], 
    [data-testid="stMarkdownContainer"] table {
        display: block !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
    }
    [data-testid="stTable"] table,
    [data-testid="stMarkdownContainer"] table {
        min-width: 600px !important;
    }
    .js-plotly-plot, .plotly, .js-plotly-plot .plot-container {
        width: 100% !important;
    }
    .stButton > button {
        font-size: 0.85rem !important;
        padding: 6px 12px !important;
        width: 100% !important;
    }
    [data-testid="stSidebar"] {
        width: 280px !important;
    }
    .stApp {
        overflow-x: hidden !important;
    }
}

/* Tablet / Small Laptop */
@media (min-width: 769px) and (max-width: 1440px) {
    .main .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-bottom: 100px !important;
    }
    .hub-title {
        font-size: 1.3rem !important;
    }
    .hub-card {
        padding: 12px 10px;
    }
    div[data-testid="stTab"] button {
        padding: 8px 16px !important;
        font-size: 0.85rem !important;
    }
}

/* Large Screens */
@media (min-width: 1400px) {
    .main .block-container {
        max-width: 1400px !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    .hub-card {
        padding: 18px 20px;
    }
}

@media (max-width: 640px) {
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        min-width: 100% !important;
        flex: 1 1 100% !important;
    }
}

[data-testid="stMetricContainer"] {
    min-height: 100px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
}

[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 800 !important;
    line-height: 1.2 !important;
    color: var(--text-strong) !important;
    letter-spacing: -0.02em !important;
}

[data-testid="stMetricLabel"] {
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

[data-testid="stMetricDelta"] {
    font-weight: 600 !important;
    margin-top: 4px;
}

@media (max-width: 640px) {
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        min-width: 100% !important;
        flex: 1 1 100% !important;
    }
    [data-testid="stMetricValue"], .metric-highlight-value {
        font-size: 1.8rem !important;
    }
    [data-testid="stMetricLabel"], .metric-highlight-label {
        font-size: 0.6rem !important;
    }
    .metric-highlight-help, .metric-icon-wrap, .metric-highlight-icon, .op-card-icon {
        display: none !important;
    }
    [data-testid="stMetricContainer"], .hub-card, .metric-highlight, .metric-icon-card, .op-card {
        min-height: auto !important;
        height: auto !important;
        padding: 12px !important;
    }
}

/* ── Sidebar Nav Pills ──────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    display: flex !important;
    align-items: center !important;
    padding: 7px 12px !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    transition: background 0.15s ease, color 0.15s ease !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    color: var(--on-surface-variant) !important;
    margin-bottom: 2px !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: rgba(var(--primary-rgb), 0.08) !important;
    color: var(--primary) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"],
[data-testid="stSidebar"] [data-testid="stRadio"] input:checked + div {
    background: rgba(var(--primary-rgb), 0.12) !important;
    color: var(--primary) !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stMarkdownContainer"] p::before,
[data-testid="stSidebar"] [data-testid="stRadio"] span[data-baseweb="radio"] > div:first-child {
    display: none !important;
}

/* ── Sync button ────────────────────────────────────────────────── */
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: var(--btn-gradient) !important;
    box-shadow: 0 4px 10px rgba(var(--primary-rgb), 0.25) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    opacity: 0.94 !important;
    box-shadow: 0 6px 14px rgba(var(--primary-rgb), 0.35) !important;
}

.strategic-intel-label {
    font-size: 0.7rem !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    font-weight: 700 !important;
    color: var(--primary) !important;
    opacity: 0.85 !important;
}

.orthodox-typewriter {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.92rem !important;
    background: var(--surface) !important;
    color: var(--on-surface) !important;
    padding: 16px 20px !important;
    border-radius: 8px !important;
    border-left: 4px solid var(--primary) !important;
    white-space: normal !important;
    display: block !important;
    width: 100% !important;
    margin-bottom: 8px !important;
    line-height: 1.65 !important;
}

.war-room-gauge .js-plotly-plot {
    min-height: 240px !important;
}

@media (max-width: 768px) {
    [data-testid="stColumn"] {
        min-width: calc(50% - 0.5rem) !important;
        flex: 1 1 calc(50% - 0.5rem) !important;
    }
}
@media (max-width: 480px) {
    [data-testid="stColumn"] {
        min-width: 100% !important;
    }
}
</style>
"""


def sidebar_branding():
    """Elegant sidebar branding to save main screen space."""
    logo_src = "https://logo.clearbit.com/deencommerce.com"
    try:
        import os

        logo_jpg = os.path.join("assets", "deen_logo.jpg")
        if os.path.exists(logo_jpg):
            logo_src = logo_jpg  # st.logo natively handles local paths
    except:
        pass
        
    # Apply the native Streamlit logo (shows at the top of the sidebar)
    st.logo(logo_src, icon_image=logo_src)

    # Add Last Synced info if available
    sync_html = ""
    if st.session_state.get("live_sync_time"):
        diff = datetime.now() - st.session_state.live_sync_time
        mins = int(diff.total_seconds() / 60)
        sync_label = "Just now" if mins < 1 else f"{mins}m ago"
        sync_html = f'<div style="font-size:0.75rem; color:#64748b; margin-top:10px;">🔄 Last Synced: {sync_label}</div>'

    # Minimal branding: Only show sync status if available
    if sync_html:
        st.markdown(f'<div class="hub-sidebar-brand">{sync_html}</div>', unsafe_allow_html=True)


def page_header():
    """Minimal page_header for the main page content area."""
    # Title is shown in the hero banner - no need to duplicate here



























def page_footer():
    """Renders a robust and persistent branding page_footer."""
    logo_src = "https://logo.clearbit.com/deencommerce.com"
    try:
        import base64

        logo_jpg = os.path.join("assets", "deen_logo.jpg")
        if os.path.exists(logo_jpg):
            with open(logo_jpg, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            logo_src = f"data:image/jpeg;base64,{b64}"
    except:
        pass

    st.markdown(
        f"""
        <div class="hub-page_footer">
            <div style="width:100%; text-align:center; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px;">
                <div style="display:flex; align-items:center; justify-content:center; gap:10px;">
                    <a href="https://deencommerce.com/" target="_blank" style="color:var(--on-surface); text-decoration:none; display:flex; align-items:center; justify-content:center; flex-wrap:wrap; gap:6px;">
                        <span style="font-size:0.9rem; opacity:0.9;">Powered by</span>
                        <img src="{logo_src}" width="18" height="18" style="border-radius:4px; margin-top:-2px;" onerror="this.style.display='none'">
                        </a>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )