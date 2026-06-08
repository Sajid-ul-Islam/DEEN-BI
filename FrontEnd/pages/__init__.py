"""Primary page registry for the Streamlit application."""

from __future__ import annotations

__all__ = ["render_intelligence_hub_page"]


def render_intelligence_hub_page() -> None:
    from .dashboard import render_intelligence_hub_page as _render_intelligence_hub_page

    return _render_intelligence_hub_page()
