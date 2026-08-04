"""Customer Cohort LTV & Predictive Churn Analytics Service."""

from __future__ import annotations
import pandas as pd
import numpy as np
from BackEnd.utils.sales_schema import ensure_sales_schema


def calculate_cohort_ltv(sales_df: pd.DataFrame) -> dict:
    """Computes monthly customer cohort LTV curves and identifies customers at risk of churn."""
    sales = ensure_sales_schema(sales_df)
    if sales.empty or "customer_key" not in sales.columns or "order_date" not in sales.columns:
        return {
            "cohort_matrix": pd.DataFrame(),
            "churn_alerts": pd.DataFrame(),
            "retention_stats": {}
        }

    sales_clean = sales.dropna(subset=["order_date", "customer_key"]).copy()
    sales_clean = sales_clean[sales_clean["customer_key"] != ""].copy()
    sales_clean["order_date"] = pd.to_datetime(sales_clean["order_date"], errors="coerce")

    # Determine First Purchase Date per Customer
    first_orders = sales_clean.groupby("customer_key")["order_date"].min().reset_index().rename(
        columns={"order_date": "cohort_month_raw"}
    )
    first_orders["cohort_month"] = first_orders["cohort_month_raw"].dt.to_period("M").astype(str)

    merged = sales_clean.merge(first_orders[["customer_key", "cohort_month", "cohort_month_raw"]], on="customer_key")
    
    # Calculate Days Elapsed Since Cohort Joining BEFORE grouping
    merged["days_since_cohort"] = (merged["order_date"] - merged["cohort_month_raw"]).dt.days

    cohort_sizes = first_orders.groupby("cohort_month")["customer_key"].nunique()

    cohort_data = []
    for cohort, group in merged.groupby("cohort_month"):
        size = cohort_sizes.get(cohort, 1) or 1
        ltv_0 = group[group["days_since_cohort"] <= 1]["order_total"].sum() / size
        ltv_30 = group[group["days_since_cohort"] <= 30]["order_total"].sum() / size
        ltv_60 = group[group["days_since_cohort"] <= 60]["order_total"].sum() / size
        ltv_90 = group[group["days_since_cohort"] <= 90]["order_total"].sum() / size
        ltv_180 = group[group["days_since_cohort"] <= 180]["order_total"].sum() / size

        cohort_data.append({
            "Cohort Month": cohort,
            "Cohort Size": size,
            "Day 0 (Initial)": round(ltv_0, 0),
            "Day 30 LTV": round(ltv_30, 0),
            "Day 60 LTV": round(ltv_60, 0),
            "Day 90 LTV": round(ltv_90, 0),
            "Day 180 LTV": round(ltv_180, 0),
        })

    if cohort_data:
        cohort_matrix = pd.DataFrame(cohort_data).sort_values("Cohort Month", ascending=False).reset_index(drop=True)
    else:
        cohort_matrix = pd.DataFrame(columns=["Cohort Month", "Cohort Size", "Day 0 (Initial)", "Day 30 LTV", "Day 60 LTV", "Day 90 LTV", "Day 180 LTV"])

    # --- Predictive Churn Risk Scoring ---
    customer_orders = sales_clean.groupby("customer_key").agg(
        first_order=("order_date", "min"),
        last_order=("order_date", "max"),
        order_count=("order_id", "nunique"),
        total_spent=("order_total", "sum")
    ).reset_index()

    customer_orders["customer_lifespan_days"] = (customer_orders["last_order"] - customer_orders["first_order"]).dt.days
    customer_orders["recency_days"] = (pd.Timestamp.now() - customer_orders["last_order"]).dt.days

    # Expected purchase cycle
    customer_orders["avg_cycle_days"] = np.where(
        customer_orders["order_count"] > 1,
        customer_orders["customer_lifespan_days"] / (customer_orders["order_count"] - 1),
        45.0  # default cycle
    )

    # Overdue factor
    customer_orders["churn_risk_score"] = np.where(
        customer_orders["avg_cycle_days"] > 0,
        customer_orders["recency_days"] / customer_orders["avg_cycle_days"],
        1.0
    )

    churn_alerts = customer_orders[
        (customer_orders["order_count"] >= 2) & (customer_orders["churn_risk_score"] >= 1.75)
    ].sort_values("total_spent", ascending=False).head(20).reset_index(drop=True)

    churn_alerts["status"] = "⚠️ Overdue for Repeat Purchase"

    return {
        "cohort_matrix": cohort_matrix,
        "churn_alerts": churn_alerts,
        "retention_stats": {
            "avg_repeat_rate": float((customer_orders["order_count"] > 1).mean() * 100.0),
            "total_tracked_customers": len(customer_orders),
            "at_risk_vip_count": len(churn_alerts)
        }
    }
