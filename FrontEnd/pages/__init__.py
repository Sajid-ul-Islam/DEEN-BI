"""Primary page registry for the Streamlit application."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .dashboard import render_intelligence_hub_page

_PAGE_RENDERERS = {
    "intelligence_hub": render_intelligence_hub_page,
}

__all__ = [
    "render_intelligence_hub_page",
]
