"""Size & Color Variant Velocity & Stockout Risk Service."""

from __future__ import annotations
import pandas as pd
import numpy as np
from BackEnd.core.categories import parse_sku_variants, get_clean_product_name
from BackEnd.utils.sales_schema import ensure_sales_schema


def analyze_variant_velocity(sales_df: pd.DataFrame, stock_df: pd.DataFrame = None) -> dict:
    """Computes size & color sell-through rates, variant velocities, and stockout risk days."""
    sales = ensure_sales_schema(sales_df)
    if sales.empty:
        return {
            "variant_df": pd.DataFrame(),
            "size_summary": pd.DataFrame(),
            "color_summary": pd.DataFrame(),
            "stockout_alerts": pd.DataFrame()
        }

    # Parse SKU variants if missing
    parsed = sales["item_name"].apply(parse_sku_variants).tolist()
    sales_copy = sales.copy()
    sales_copy["color"] = [p[0] for p in parsed]
    sales_copy["size"] = [p[1] for p in parsed]
    sales_copy["clean_name"] = sales_copy["item_name"].apply(get_clean_product_name)

    # Date range for velocity calculation
    if "order_date" in sales_copy.columns and sales_copy["order_date"].notna().any():
        days_span = (sales_copy["order_date"].max() - sales_copy["order_date"].min()).days or 1
    else:
        days_span = 30

    # Group by Variant (Clean Name + Color + Size)
    variant_df = sales_copy.groupby(["clean_name", "color", "size", "Category"], as_index=False).agg(
        total_sold=("qty", "sum"),
        total_revenue=("order_total", "sum"),
        orders_count=("order_id", "nunique")
    )
    variant_df["daily_velocity"] = variant_df["total_sold"] / days_span

    # Merge with Stock Data if provided
    if stock_df is not None and not stock_df.empty:
        stock_copy = stock_df.copy()
        stock_copy["stock_qty"] = pd.to_numeric(stock_copy.get("Stock Quantity", 0), errors="coerce").fillna(0)
        stock_copy["clean_name"] = stock_copy.get("Name", "").apply(get_clean_product_name)
        
        parsed_stock = stock_copy.get("Name", pd.Series(dtype=str)).apply(parse_sku_variants).tolist()
        stock_copy["color"] = [p[0] for p in parsed_stock]
        stock_copy["size"] = [p[1] for p in parsed_stock]

        stock_agg = stock_copy.groupby(["clean_name", "color", "size"], as_index=False)["stock_qty"].sum()
        variant_df = variant_df.merge(stock_agg, on=["clean_name", "color", "size"], how="left")
        variant_df["stock_qty"] = variant_df["stock_qty"].fillna(0)
    else:
        variant_df["stock_qty"] = 0

    variant_df["days_of_stock"] = np.where(
        variant_df["daily_velocity"] > 0,
        variant_df["stock_qty"] / variant_df["daily_velocity"],
        999.0
    )
    variant_df["sell_through_rate"] = np.where(
        (variant_df["stock_qty"] + variant_df["total_sold"]) > 0,
        (variant_df["total_sold"] / (variant_df["stock_qty"] + variant_df["total_sold"])) * 100.0,
        0.0
    )

    # Size Summary
    size_summary = sales_copy[sales_copy["size"] != "Unknown"].groupby("size", as_index=False).agg(
        units_sold=("qty", "sum"),
        revenue=("order_total", "sum")
    ).sort_values("units_sold", ascending=False).reset_index(drop=True)

    # Color Summary
    color_summary = sales_copy[sales_copy["color"] != "Unknown"].groupby("color", as_index=False).agg(
        units_sold=("qty", "sum"),
        revenue=("order_total", "sum")
    ).sort_values("units_sold", ascending=False).head(15).reset_index(drop=True)

    # Stockout Risk Alerts (stock < 7 days of velocity and daily_velocity > 0.5)
    alerts = variant_df[(variant_df["days_of_stock"] <= 7) & (variant_df["daily_velocity"] >= 0.3)].sort_values(
        "days_of_stock"
    ).reset_index(drop=True)

    return {
        "variant_df": variant_df,
        "size_summary": size_summary,
        "color_summary": color_summary,
        "stockout_alerts": alerts
    }
