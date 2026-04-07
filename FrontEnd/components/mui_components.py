import streamlit as st
from streamlit_elements import elements, mui, html

def mui_stat_card(label: str, value: str, icon: str = "analytics", color: str = "primary"):
    """
    Renders a Material UI Paper card with an icon and typography.
    Requires streamlit-elements.
    """
    with elements(f"mui_card_{label}"):
        with mui.Paper(
            elevation=1,
            sx={
                "p": 2,
                "borderRadius": "28px",
                "display": "flex",
                "alignItems": "center",
                "gap": 2,
                "minWidth": 200,
                "bgcolor": "background.paper",
                "border": "1px solid",
                "borderColor": "divider",
            }
        ):
            with mui.Box(
                sx={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "bgcolor": f"{color}.main",
                    "color": "white",
                    "borderRadius": "12px",
                    "width": 48,
                    "height": 48,
                }
            ):
                mui.icon.getattr(icon)()
                
            with mui.Box():
                mui.Typography(label, variant="overline", sx={"fontWeight": 600, "color": "text.secondary"})
                mui.Typography(value, variant="h5", sx={"fontWeight": 700})

def render_mui_dashboard_sync():
    """Example of an MUI-based sync status indicator."""
    with elements("mui_sync"):
        with mui.Box(sx={"display": "flex", "alignItems": "center", "gap": 1, "mb": 2}):
            mui.CircularProgress(size=20, thickness=5)
            mui.Typography("Synchronizing with WooCommerce...", variant="body2", sx={"color": "primary.main", "fontWeight": 500})
