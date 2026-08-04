import pytest
import streamlit as st
from FrontEnd.components.layout import THEMES, setup_theme
from FrontEnd.components.charts import get_active_theme_palette, apply_plotly_theme, build_discrete_color_map
from FrontEnd.utils.state import init_state, save_state, load_state

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


def test_themes_registry_completeness():
    """Verify that all theme presets contain required keys."""
    expected_keys = [
        "name", "icon", "description", "primary", "primary_rgb",
        "secondary", "accent", "gradient_1", "btn_gradient",
        "download_gradient", "download_shadow", "chart_scale", "chart_colors"
    ]
    assert len(THEMES) >= 6
    for theme_name, theme_data in THEMES.items():
        for key in expected_keys:
            assert key in theme_data, f"Missing key {key} in theme {theme_name}"


def test_theme_palette_retrieval():
    """Verify that get_active_theme_palette responds to session_state theme_choice."""
    st.session_state["theme_choice"] = "Cyberpunk Neon"
    palette = get_active_theme_palette()
    assert palette["name"] == "Cyberpunk Neon"
    assert palette["primary"] == "#06B6D4"

    st.session_state["theme_choice"] = "Emerald Forest"
    palette = get_active_theme_palette()
    assert palette["name"] == "Emerald Forest"
    assert palette["primary"] == "#10B981"


def test_apply_plotly_theme_incorporates_active_theme():
    """Verify that apply_plotly_theme injects the current theme colorway into Plotly figures."""
    if not HAS_PLOTLY:
        pytest.skip("Plotly not installed")

    st.session_state["theme_choice"] = "Sunset Amber"
    fig = go.Figure(data=[go.Bar(x=[1, 2], y=[3, 4])])
    themed_fig = apply_plotly_theme(fig)

    assert themed_fig is not None
    layout = themed_fig.layout
    assert layout.colorway is not None
    assert layout.colorway[0] == "#F97316"
    assert layout.hoverlabel.bordercolor == "#F97316"


def test_build_discrete_color_map_theme_scale():
    """Verify build_discrete_color_map defaults to theme's color scale."""
    if not HAS_PLOTLY:
        pytest.skip("Plotly not installed")

    st.session_state["theme_choice"] = "Emerald Forest"
    color_map = build_discrete_color_map(["T-Shirt", "Pants", "Jacket"])
    assert len(color_map) == 3
    assert "T-Shirt" in color_map


def test_theme_state_persistence():
    """Verify that theme_choice persists in state initialization."""
    st.session_state.pop("theme_choice", None)
    init_state()
    assert "theme_choice" in st.session_state
    assert st.session_state["theme_choice"] in THEMES
