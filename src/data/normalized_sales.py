from __future__ import annotations

import pandas as pd

from src.core.categories import get_category_for_sales
from src.utils.data import find_columns, parse_dates


CANONICAL_COLUMNS = [
    "source_tab",
    "order_id",
    "order_date",
    "customer_name",
    "phone",
    "email",
    "state",
    "address",
    "sku",
    "item_name",
    "qty",
    "unit_price",
    "order_total",
    "store",
    "payment_method",
    "trx_id",
    "customer_note",
    "archive_status",
    "order_status",
    "category",
    "line_amount",
]


def _first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_map = {str(col).strip().lower(): col for col in df.columns}
    for candidate in candidates:
        hit = lower_map.get(candidate.lower())
        if hit:
            return hit
    return None


def normalize_sales_dataframe(
    raw_df: pd.DataFrame, source_tab: str = ""
) -> tuple[pd.DataFrame, dict[str, str]]:
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS), {}

    df = raw_df.copy()
    detected = find_columns(df)

    normalized = pd.DataFrame(index=df.index)
    normalized["source_tab"] = source_tab or ""

    normalized["order_id"] = _series_as_text(df, detected.get("order_id"))
    normalized["order_date"] = (
        parse_dates(df[detected["date"]]) if detected.get("date") in df.columns else pd.NaT
    )
    normalized["customer_name"] = _series_as_text(
        df, detected.get("customer_name"), default="Unknown Customer"
    )
    normalized["phone"] = _series_as_text(df, detected.get("phone"))
    normalized["email"] = _series_as_text(df, detected.get("email"))
    normalized["state"] = _series_as_text(
        df, _first_existing(df, ["State Name (Billing)", "State", "City", "Zone"])
    )
    normalized["address"] = _series_as_text(
        df, _first_existing(df, ["Address 1&2 (Shipping)", "Address", "Shipping Address"])
    )
    normalized["sku"] = _series_as_text(df, _first_existing(df, ["SKU", "Sku"]))
    normalized["item_name"] = _series_as_text(
        df, detected.get("name"), default="Unknown Product"
    )
    normalized["qty"] = _series_as_number(df, detected.get("qty"))
    normalized["unit_price"] = _series_as_number(df, detected.get("cost"))
    normalized["order_total"] = _series_as_number(
        df, _first_existing(df, ["Order Total Amount", "Order Total", "Total"])
    )
    normalized["store"] = _series_as_text(df, _first_existing(df, ["Store"]))
    normalized["payment_method"] = _series_as_text(
        df, _first_existing(df, ["Payment Method Title", "Payment Method"])
    )
    normalized["trx_id"] = _series_as_text(df, _first_existing(df, ["trxId", "Transaction ID"]))
    normalized["customer_note"] = _series_as_text(
        df, _first_existing(df, ["Customer Note", "Note", "Notes"])
    )
    normalized["archive_status"] = _series_as_text(
        df,
        _first_existing(
            df,
            ["Archive Status", "Sync Status", "Sync to 2026", "Archive to 2026"],
        ),
    )
    normalized["order_status"] = _series_as_text(
        df, _first_existing(df, ["Order Status", "Status", "Fulfillment Status"])
    )

    normalized["category"] = normalized["item_name"].apply(get_category_for_sales)
    normalized["line_amount"] = normalized["qty"] * normalized["unit_price"]
    normalized["order_key"] = (
        normalized["order_id"]
        .where(normalized["order_id"].ne(""))
        .fillna("")
    )
    fallback = (
        normalized["phone"].where(normalized["phone"].ne("")).fillna("")
        + "|"
        + normalized["email"].where(normalized["email"].ne("")).fillna("")
        + "|"
        + normalized["customer_name"].fillna("")
        + "|"
        + normalized["order_date"].astype(str).replace("NaT", "")
    )
    normalized["order_key"] = normalized["order_key"].where(
        normalized["order_key"].ne(""), fallback
    )

    normalized = normalized[CANONICAL_COLUMNS + ["order_key"]]
    return normalized, detected


def compute_sales_analytics(normalized_df: pd.DataFrame) -> dict[str, pd.DataFrame | dict | str]:
    if normalized_df is None or normalized_df.empty:
        return {
            "timeframe": "",
            "summary": pd.DataFrame(),
            "drilldown": pd.DataFrame(),
            "top_products": pd.DataFrame(),
            "top_customers": pd.DataFrame(),
            "basket": {"avg_basket_qty": 0, "avg_basket_value": 0, "total_orders": 0},
        }

    df = normalized_df.copy()
    if "order_date" in df.columns:
        date_series = pd.to_datetime(df["order_date"], errors="coerce").dropna()
        timeframe = ""
        if not date_series.empty:
            timeframe = (
                f"{date_series.min().strftime('%d%b')}_to_{date_series.max().strftime('%d%b_%y')}"
            )
    else:
        timeframe = ""

    summary = (
        df.groupby("category")
        .agg({"qty": "sum", "line_amount": "sum"})
        .reset_index()
        .rename(columns={"category": "Category", "qty": "Total Qty", "line_amount": "Total Amount"})
    )
    if not summary.empty:
        total_rev = summary["Total Amount"].sum()
        total_qty = summary["Total Qty"].sum()
        if total_rev > 0:
            summary["Revenue Share (%)"] = ((summary["Total Amount"] / total_rev) * 100).round(2)
        if total_qty > 0:
            summary["Quantity Share (%)"] = ((summary["Total Qty"] / total_qty) * 100).round(2)

    drilldown = (
        df.groupby(["category", "unit_price"])
        .agg({"qty": "sum", "line_amount": "sum"})
        .reset_index()
        .rename(
            columns={
                "category": "Category",
                "unit_price": "Price (TK)",
                "qty": "Total Qty",
                "line_amount": "Total Amount",
            }
        )
    )

    top_products = (
        df.groupby("item_name")
        .agg({"qty": "sum", "line_amount": "sum", "category": "first"})
        .reset_index()
        .rename(
            columns={
                "item_name": "Product Name",
                "qty": "Total Qty",
                "line_amount": "Total Amount",
                "category": "Category",
            }
        )
        .sort_values("Total Amount", ascending=False)
    )

    top_customers = (
        df[df["customer_name"].fillna("").ne("")]
        .groupby("customer_name")
        .agg({"line_amount": "sum", "qty": "sum"})
        .reset_index()
        .rename(
            columns={
                "customer_name": "Customer Name",
                "line_amount": "Total Spent",
                "qty": "Items Purchased",
            }
        )
        .sort_values("Total Spent", ascending=False)
    )

    basket_df = (
        df[df["order_key"].fillna("").ne("")]
        .groupby("order_key")
        .agg({"qty": "sum", "line_amount": "sum"})
    )
    basket = {"avg_basket_qty": 0, "avg_basket_value": 0, "total_orders": 0}
    if not basket_df.empty:
        basket = {
            "avg_basket_qty": float(basket_df["qty"].mean()),
            "avg_basket_value": float(basket_df["line_amount"].mean()),
            "total_orders": int(len(basket_df)),
        }

    return {
        "timeframe": timeframe,
        "summary": summary,
        "drilldown": drilldown,
        "top_products": top_products,
        "top_customers": top_customers,
        "basket": basket,
    }


def _series_as_text(df: pd.DataFrame, column: str | None, default: str = "") -> pd.Series:
    if not column or column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype="object")
    series = df[column].fillna(default).astype(str).str.strip()
    return series.replace({"nan": default, "None": default})


def _series_as_number(df: pd.DataFrame, column: str | None) -> pd.Series:
    if not column or column not in df.columns:
        return pd.Series([0] * len(df), index=df.index, dtype="float64")
    return pd.to_numeric(df[column], errors="coerce").fillna(0)
