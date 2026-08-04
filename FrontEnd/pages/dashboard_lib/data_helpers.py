import pandas as pd
import polars as pl
from BackEnd.utils.sales_schema import ensure_sales_schema

def apply_global_filters(df: pd.DataFrame, categories: list[str] = None, statuses: list[str] = None) -> pd.DataFrame:
    """Applies global filters with hierarchical matching for categories and strict matching for statuses."""
    if df.empty:
        return df
    
    lz_df = pl.from_pandas(df).lazy()
    
    # 1. Category Filter (Hierarchical)
    if categories and "All" not in categories:
        import re
        # Create regex pattern for startswith matching across multiple categories
        escaped_cats = [re.escape(c) for c in categories]
        pattern = "^(" + "|".join(escaped_cats) + ")"
        lz_df = lz_df.filter(pl.col("Category").str.contains(pattern))
        
    # 2. Status Filter
    if statuses and "All" not in statuses:
        lower_statuses = [s.lower() for s in statuses]
        lz_df = lz_df.filter(pl.col("order_status").str.to_lowercase().is_in(lower_statuses))
        
    return lz_df.collect().to_pandas()

def get_available_filters(df: pd.DataFrame):
    """Returns master category list and statuses for global filter controls.
    
    Uses the centralized master category list to ensure consistent
    hierarchy display regardless of data availability.
    """
    from BackEnd.core.categories import get_master_category_list
    
    # Always return the complete master category list (preserves custom order)
    unique_cats = get_master_category_list()
    
    # Statuses - keep sorted as order doesn't matter for statuses
    unique_statuses = sorted([str(s).title() for s in df["order_status"].dropna().unique()]) if not df.empty else []
    
    return unique_cats, unique_statuses

def prune_dataframe(df: pd.DataFrame, preferred_columns: list[str]) -> pd.DataFrame:
    sales = ensure_sales_schema(df)
    
    # Ensure all preferred columns exist, fill missing with pd.NA
    for col in preferred_columns:
        if col not in sales.columns:
            sales[col] = pd.NA
    return sales[preferred_columns].copy()

def build_order_level_dataset(df: pd.DataFrame) -> pd.DataFrame:
    sales = ensure_sales_schema(df)
    if sales.empty:
        return pd.DataFrame()

    optional_columns = [col for col in ["order_day", "day_name", "day_num", "hour", "region", "_import_time"] if col in sales.columns]
    
    # Clean Pandas NA to None for seamless Polars conversion
    sales_clean = sales.copy()
    order_id_clean = sales_clean["order_id"].astype(str).str.strip()
    import numpy as np
    sales_clean["order_id"] = np.where(order_id_clean.isin(["", "nan", "None", "NaN", "<NA>"]), None, order_id_clean)
    
    from BackEnd.utils.sales_schema import estimate_line_revenue
    sales_clean["clean_line_rev"] = estimate_line_revenue(sales_clean)
    
    # Supercharge GroupBy utilizing Polars LazyFrame
    lz_df = pl.from_pandas(sales_clean).lazy()
    
    lz_valid = lz_df.filter(pl.col("order_id").is_not_null())
    lz_missing = lz_df.filter(pl.col("order_id").is_null())
    
    meta_cols = ["shipped_date", "customer_key", "customer_name", "order_status", "source", "city", "state"] + optional_columns
    available_meta = [c for c in meta_cols if c in sales_clean.columns]
    
    # Perform aggregations on valid orders (summing line revenues excludes cashback)
    agg_exprs = [
        pl.col("order_date").min().alias("order_date"),
        pl.col("clean_line_rev").sum().alias("order_total"),
        pl.col("qty").sum().alias("qty"),
    ]

    
    # Pick the first non-null string metadata element
    for col in available_meta:
        agg_exprs.append(pl.col(col).drop_nulls().first().alias(col))
        
    lz_grouped = lz_valid.sort("order_date").group_by("order_id").agg(agg_exprs)
    
    # Execute query plans in parallel
    grouped_orders = lz_grouped.collect().to_pandas()
    passthrough_rows = lz_missing.collect().to_pandas()

    available_cols = ["order_id", "order_date", "order_total", "customer_key", "customer_name", "order_status", "source", "city", "state", "qty"] + optional_columns
    if not passthrough_rows.empty:
        passthrough_rows = passthrough_rows[[c for c in available_cols if c in passthrough_rows.columns]]
        
    frames = [frame for frame in [grouped_orders, passthrough_rows] if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=available_cols)
    
    final_df = pd.concat(frames, ignore_index=True, sort=False)
    
    # Final formatting cleanup
    if "order_total" in final_df.columns:
        final_df["order_total"] = pd.to_numeric(final_df["order_total"], errors="coerce").fillna(0.0)
    if "qty" in final_df.columns:
        final_df["qty"] = pd.to_numeric(final_df["qty"], errors="coerce").fillna(0).astype(int)
        
    return final_df

def sum_order_level_revenue(df: pd.DataFrame, order_df: pd.DataFrame = None) -> float:
    orders = order_df if order_df is not None else build_order_level_dataset(df)
    if orders.empty:
        return 0.0
    return float(pd.to_numeric(orders["order_total"], errors="coerce").fillna(0).sum())
