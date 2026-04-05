"""Primary page registry for the Streamlit application."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .customer_insights import render_customer_insight_tab
from .dashboard import render_dashboard_tab
from .system_health import render_system_health_tab
from .woocommerce import render_woocommerce_tab
from .cycle_analytics import render_cycle_analytics_tab
from FrontEnd.utils.config import PRIMARY_PAGE_CONFIG


@dataclass(frozen=True)
class PrimaryPage:
    key: str
    label: str
    description: str
    render: Callable[[], None]


_PAGE_RENDERERS = {
    "business_intelligence": render_dashboard_tab,
    "customer_intelligence": render_customer_insight_tab,
    "commerce_hub": render_woocommerce_tab,
    "business_cycles": render_cycle_analytics_tab,
    "system_health": render_system_health_tab,
}


def get_primary_pages() -> tuple[PrimaryPage, ...]:
    return tuple(
        PrimaryPage(
            key=page["key"],
            label=page["label"],
            description=page["description"],
            render=_PAGE_RENDERERS[page["key"]],
        )
        for page in PRIMARY_PAGE_CONFIG
    )


__all__ = [
    "PrimaryPage",
    "get_primary_pages",
    "render_dashboard_tab",
    "render_customer_insight_tab",
    "render_woocommerce_tab",
    "render_cycle_analytics_tab",
    "render_system_health_tab",
]
