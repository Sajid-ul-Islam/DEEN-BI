"""Primary page registry for the Streamlit application."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .dashboard import render_intelligence_hub_page
from .commerce_ops import render_commerce_ops_page
from .shopai import render_shopai_tab
from .system_health import render_system_health_tab

from FrontEnd.utils.config import PRIMARY_PAGE_CONFIG


@dataclass(frozen=True)
class PrimaryPage:
    key: str
    label: str
    description: str
    render: Callable[[], None]


_PAGE_RENDERERS = {
    "intelligence_hub": render_intelligence_hub_page,
    "commerce_ops": render_commerce_ops_page,
    "shop_ai_crm": render_shopai_tab,
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
    "render_shopai_tab",
    "render_orders_analytics_tab",
    "render_operations_hub_tab",
    "render_system_health_tab",
]
