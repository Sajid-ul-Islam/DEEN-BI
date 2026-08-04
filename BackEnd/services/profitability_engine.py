"""Contribution Margin (CM1 & CM2) Unit Profitability Engine."""

from __future__ import annotations
import pandas as pd
import numpy as np
from BackEnd.utils.sales_schema import ensure_sales_schema, estimate_line_revenue
from BackEnd.services.returns_tracker import load_returns_data, get_current_sync_window


def calculate_contribution_margin(sales_df: pd.DataFrame, cogs_margin: float = 0.45, avg_courier_fee: float = 120.0, avg_ad_spend_per_order: float = 150.0) -> dict:
    """Computes CM1 and CM2 financial metrics.
    
    CM1 = Net Sales - COGS
    CM2 = CM1 - (Courier Fees + Return Loss + Ad Spend)
    """
    sales = ensure_sales_schema(sales_df)
    if sales.empty:
        return {
            "gross_sales": 0.0,
            "net_sales": 0.0,
            "cogs": 0.0,
            "cm1": 0.0,
            "cm1_margin": 0.0,
            "courier_cost": 0.0,
            "ad_spend": 0.0,
            "return_loss": 0.0,
            "cm2": 0.0,
            "cm2_margin": 0.0,
            "product_profitability": pd.DataFrame()
        }

    # Gross sales excluding promotional cashback
    sales_copy = sales.copy()
    sales_copy["line_rev"] = estimate_line_revenue(sales_copy)
    gross_sales = float(sales_copy["line_rev"].sum())

    # Returns Financial Loss
    return_loss = 0.0
    try:
        window = get_current_sync_window()
        returns_df = load_returns_data(sync_window=window, sales_df=sales_copy)
        if not returns_df.empty and "partial_amount" in returns_df.columns:
            return_loss = float(pd.to_numeric(returns_df["partial_amount"], errors="coerce").fillna(0.0).sum())
    except Exception:
        return_loss = float(gross_sales * 0.05)  # 5% estimate fallback

    net_sales = max(0.0, gross_sales - return_loss)
    cogs = float(net_sales * cogs_margin)
    cm1 = net_sales - cogs
    cm1_margin = (cm1 / net_sales * 100.0) if net_sales else 0.0

    total_orders = float(sales_copy["order_id"].nunique() or 1)
    courier_cost = float(total_orders * avg_courier_fee)
    ad_spend = float(total_orders * avg_ad_spend_per_order)

    cm2 = cm1 - (courier_cost + ad_spend + return_loss)
    cm2_margin = (cm2 / net_sales * 100.0) if net_sales else 0.0

    # Product Level Contribution Margin
    prod_df = sales_copy.groupby(["item_name", "Category"], as_index=False).agg(
        units_sold=("qty", "sum"),
        gross_revenue=("line_rev", "sum")
    )
    prod_df["est_cogs"] = prod_df["gross_revenue"] * cogs_margin
    prod_df["cm1_profit"] = prod_df["gross_revenue"] - prod_df["est_cogs"]
    prod_df["cm1_margin_%"] = (prod_df["cm1_profit"] / prod_df["gross_revenue"].replace(0, 1)) * 100.0
    prod_df = prod_df.sort_values("cm1_profit", ascending=False).reset_index(drop=True)

    return {
        "gross_sales": gross_sales,
        "net_sales": net_sales,
        "cogs": cogs,
        "cm1": cm1,
        "cm1_margin": cm1_margin,
        "courier_cost": courier_cost,
        "ad_spend": ad_spend,
        "return_loss": return_loss,
        "cm2": cm2,
        "cm2_margin": cm2_margin,
        "product_profitability": prod_df
    }
