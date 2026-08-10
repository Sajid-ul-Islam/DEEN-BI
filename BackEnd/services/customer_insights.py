"""Customer insights service built on the normalized hybrid sales schema."""

from __future__ import annotations

import hashlib
from typing import Optional

import pandas as pd
import streamlit as st

from BackEnd.services.hybrid_data_loader import load_full_woocommerce_history, load_hybrid_data
from BackEnd.utils.sales_schema import ensure_sales_schema
from BackEnd.utils.woocommerce_helpers import clean_phone, clean_email, normalize_name
from FrontEnd.utils.error_handler import log_error
from BackEnd.services.customer_manager import load_customer_mapping

CUSTOMER_BASE_COLUMNS = [
    "order_id",
    "order_date",
    "customer_name",
    "phone",
    "email",
    "item_name",
    "order_total",
    "customer_key",
]






def generate_customer_id(customer_key, email: str, phone: str, order_id: str = "") -> str:
    # 1. Registered Customer priority
    uid = str(customer_key).strip() if pd.notna(customer_key) else ""
    if uid and uid not in ["0", "0.0", "nan", "None"]:
        return f"reg_{uid}"
        
    # 2. Unregistered guests group by unique phone number first
    clean_p = clean_phone(phone)
    if clean_p:
        return f"guest_p_{clean_p}"
        
    # 3. Fallback to email or order_id
    clean_e = clean_email(email)
    if clean_e:
        return f"guest_e_{hashlib.md5(clean_e.encode()).hexdigest()[:8]}"
        
    return f"anon_{order_id}"


@st.cache_data(ttl=1800)
def generate_customer_insights(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_woocommerce: bool = True,
) -> pd.DataFrame:
    # Customer insights exclusively use WooCommerce order history.
    df = load_hybrid_data(start_date, end_date, include_woocommerce=include_woocommerce)
    full_history = load_full_woocommerce_history(end_date=end_date) if include_woocommerce else pd.DataFrame()
    return generate_customer_insights_from_sales(df, full_history_df=full_history)


def generate_customer_insights_from_sales(
    df: pd.DataFrame,
    full_history_df: pd.DataFrame | None = None,
    include_rfm: bool = True,
    include_favorites: bool = True,
) -> pd.DataFrame:
    if df.empty:
        res = pd.DataFrame(columns=[
            "customer_id", "primary_name", "all_emails", "all_phones", 
            "total_orders", "total_revenue", "avg_order_value", "first_order", 
            "last_order", "customer_lifespan_days", "recency_days", 
            "purchase_cycle_days", "clv", "segment", "r_score", "f_score", 
            "m_score", "rfm_score", "rfm_avg", "favorite_product"
        ])
        # Type enforcement for empty result
        res["first_order"] = pd.to_datetime(res["first_order"])
        res["last_order"] = pd.to_datetime(res["last_order"])
        res["total_revenue"] = pd.to_numeric(res["total_revenue"])
        res["total_orders"] = pd.to_numeric(res["total_orders"])
        res["recency_days"] = pd.to_numeric(res["recency_days"])
        return res

    df = _prepare_customer_identity(df)

    try:
        result = _aggregate_customer_metrics(df)
        current_window = result[
            [
                "customer_id",
                "total_orders",
                "total_revenue",
                "avg_order_value",
                "first_order",
                "last_order",
                "customer_lifespan_days",
                "recency_days",
                "purchase_cycle_days",
                "clv",
            ]
        ].copy()
        current_window = current_window.rename(
            columns={
                "total_orders": "current_orders",
                "total_revenue": "current_revenue",
                "avg_order_value": "current_avg_order_value",
                "first_order": "current_first_order",
                "last_order": "current_last_order",
                "customer_lifespan_days": "current_lifespan_days",
                "recency_days": "current_recency_days",
                "purchase_cycle_days": "current_purchase_cycle_days",
                "clv": "current_clv",
            }
        )

        if isinstance(full_history_df, pd.DataFrame) and not full_history_df.empty:
            history_prepared = _prepare_customer_identity(full_history_df)
            history_metrics = _aggregate_customer_metrics(history_prepared)
            if not history_metrics.empty:
                result = result.drop(
                    columns=[
                        "total_orders",
                        "total_revenue",
                        "avg_order_value",
                        "first_order",
                        "last_order",
                        "customer_lifespan_days",
                        "recency_days",
                        "purchase_cycle_days",
                        "clv",
                    ],
                    errors="ignore",
                ).merge(
                    history_metrics[
                        [
                            "customer_id",
                            "total_orders",
                            "total_revenue",
                            "avg_order_value",
                            "first_order",
                            "last_order",
                            "customer_lifespan_days",
                            "recency_days",
                            "purchase_cycle_days",
                            "clv",
                        ]
                    ],
                    on="customer_id",
                    how="left",
                )
        result = result.merge(current_window, on="customer_id", how="left")
        
        # --- RETURN RATE ENRICHMENT ---
        result = _enrich_with_returns(result, full_history_df)
        
        if include_rfm:
            result = calculate_rfm_scores(result)
            result = classify_rfm_segments(result)
        else:
            result["r_score"] = pd.NA
            result["f_score"] = pd.NA
            result["m_score"] = pd.NA
            result["rfm_score"] = ""
            result["rfm_avg"] = pd.NA
            result["segment"] = result.apply(_classify_without_rfm, axis=1)

        if include_favorites:
            favorite_products = get_favorite_products(df)
            if not favorite_products.empty:
                result = result.merge(favorite_products, on="customer_id", how="left")
                
        # Remove redundant 'Unnamed' or blank artifact customers
        invalid_names = ["unnamed", "unknown", "nan", "none", ""]
        result = result[~result["primary_name"].astype(str).str.strip().str.lower().isin(invalid_names)]
        
        return result.sort_values("total_revenue", ascending=False).reset_index(drop=True)
    except Exception as exc:
        log_error(exc, context="Customer Insights Generation")
        return pd.DataFrame()



def _aggregate_customer_metrics(df: pd.DataFrame) -> pd.DataFrame:
    import polars as pl
    if df.empty:
        return pd.DataFrame()
        
    df = df.copy()
    if "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

    lz_df = pl.from_pandas(df).lazy()  # type: ignore
    
    lz_df = lz_df.with_columns([
        pl.col("clean_email").fill_null("").cast(pl.String),
        pl.col("clean_phone").fill_null("").cast(pl.String),
        pl.col("normalized_name").fill_null("").cast(pl.String)
    ])
    
    invalid_names = ["unknown", "unnamed", "nan", "none", ""]
    
    agg_exprs = [
        pl.col("normalized_name")
          .filter(~pl.col("normalized_name").str.to_lowercase().str.strip_chars().is_in(invalid_names))
          .first().fill_null("Unknown").alias("primary_name"),
        pl.col("clean_email").filter(pl.col("clean_email") != "").unique().sort().str.join(", ").alias("all_emails"),
        pl.col("clean_phone").filter(pl.col("clean_phone") != "").unique().sort().str.join(", ").alias("all_phones"),
        pl.col("order_id").filter(pl.col("order_id").is_not_null() & (pl.col("order_id").cast(pl.String) != "")).n_unique().alias("total_orders"),
        pl.col("order_total").sum().alias("total_revenue"),
        pl.col("order_date").min().alias("first_order"),
        pl.col("order_date").max().alias("last_order"),
        pl.col("order_total").mean().alias("avg_order_value"),
    ]
    
    result_lz = lz_df.group_by("customer_id").agg(agg_exprs)
    
    result_lz = result_lz.with_columns(
        ((pl.col("last_order") - pl.col("first_order")).dt.total_days()).fill_null(0).alias("customer_lifespan_days")
    )
    
    today = pd.Timestamp.now().normalize()
    
    result_lz = result_lz.with_columns([
        (pl.lit(today) - pl.col("last_order").dt.truncate("1d")).dt.total_days().fill_null(9999).alias("recency_days"),
        pl.when(pl.col("total_orders") > 1)
          .then((pl.col("customer_lifespan_days") / (pl.col("total_orders") - 1)).round(0))
          .otherwise(pl.lit(None))
          .alias("purchase_cycle_days"),
        pl.col("total_revenue").alias("clv")
    ])
    
    result = result_lz.collect().to_pandas()
    return result


def _prepare_customer_identity(df: pd.DataFrame) -> pd.DataFrame:
    prepared = ensure_sales_schema(_select_customer_columns(df)).copy()
    prepared["normalized_name"] = prepared["customer_name"].apply(normalize_name)
    prepared["clean_email"] = prepared["email"].apply(clean_email)
    prepared["clean_phone"] = prepared["phone"].apply(clean_phone)
    
    # Try to use pre-computed mapping for stable customer IDs
    mapping_df = load_customer_mapping()
    if not mapping_df.empty:
        # Create lookup maps
        phone_to_id = {}
        email_to_id = {}
        for _, row in mapping_df.iterrows():
            cid = row["customer_id"]
            for p in str(row["phones"]).split(", "):
                if p: phone_to_id[p] = cid
            for e in str(row["emails"]).split(", "):
                if e: email_to_id[e] = cid
        
        def get_mapped_id(row):
            p = row["clean_phone"]
            e = row["clean_email"]
            return phone_to_id.get(p) or email_to_id.get(e) or generate_customer_id(
                row.get("customer_key"), e, p, row.get("order_id", "")
            )
            
        prepared["customer_id"] = prepared.apply(get_mapped_id, axis=1)
    else:
        prepared["customer_id"] = prepared.apply(
            lambda row: generate_customer_id(
                row.get("customer_key"),
                row.get("clean_email", ""), 
                row.get("clean_phone", ""), 
                row.get("order_id", "")
            ),
            axis=1,
        )
        
    # Intelligently merge 'Unknown' profiles if they share the same valid phone number
    invalid_names = ["unknown", "unnamed", "nan", "none", ""]
    valid_profiles = prepared[~prepared["normalized_name"].astype(str).str.lower().str.strip().isin(invalid_names)]
    
    if not valid_profiles.empty:
        # Get the most recent valid customer_id for each phone
        phone_to_valid_id = valid_profiles[valid_profiles["clean_phone"] != ""].drop_duplicates("clean_phone", keep="last").set_index("clean_phone")["customer_id"].to_dict()
        # Get the most recent valid customer_id for each email
        email_to_valid_id = valid_profiles[valid_profiles["clean_email"] != ""].drop_duplicates("clean_email", keep="last").set_index("clean_email")["customer_id"].to_dict()
        
        def refine_unknown_profiles(row):
            is_invalid = str(row.get("normalized_name", "")).lower().strip() in invalid_names
            phone = row.get("clean_phone", "")
            email = row.get("clean_email", "")
            if is_invalid:
                if phone and phone in phone_to_valid_id:
                    return phone_to_valid_id[phone]
                if email and email in email_to_valid_id:
                    return email_to_valid_id[email]
            return row["customer_id"]
            
        prepared["customer_id"] = prepared.apply(refine_unknown_profiles, axis=1)
        
    return prepared


def _select_customer_columns(df: pd.DataFrame) -> pd.DataFrame:
    sales = ensure_sales_schema(df)
    available = [col for col in CUSTOMER_BASE_COLUMNS if col in sales.columns]
    if not available:
        return sales
    return sales[available].copy()





def calculate_rfm_scores(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    def _score(series: pd.Series, labels: list[int], ascending: bool) -> pd.Series:
        numeric = pd.to_numeric(series, errors="coerce").fillna(series.max() if ascending else series.min())
        ranked = numeric.rank(method="average", pct=True, ascending=ascending)
        bins = pd.cut(ranked, bins=5, labels=labels, include_lowest=True)
        return bins.astype(int)

    result["r_score"] = _score(result["recency_days"], [5, 4, 3, 2, 1], ascending=False)
    result["f_score"] = _score(result["total_orders"], [1, 2, 3, 4, 5], ascending=True)
    result["m_score"] = _score(result["total_revenue"], [1, 2, 3, 4, 5], ascending=True)
    
    # Reliability Score based on return rate (lower return rate is better)
    if "return_rate" in result.columns:
        result["rel_score"] = _score(result["return_rate"], [5, 4, 3, 2, 1], ascending=False)
    else:
        result["rel_score"] = 5
        
    result["rfm_score"] = result["r_score"].astype(str) + result["f_score"].astype(str) + result["m_score"].astype(str)
    result["rfm_avg"] = (result["r_score"] + result["f_score"] + result["m_score"] + result["rel_score"]) / 4
    return result


def _enrich_with_returns(customers_df: pd.DataFrame, full_history_df: pd.DataFrame | None) -> pd.DataFrame:
    """Enrich customers DataFrame with return rate metrics."""
    returns_df = st.session_state.get("returns_data", pd.DataFrame())
    if returns_df is None or returns_df.empty or full_history_df is None or full_history_df.empty:
        customers_df["return_count"] = 0
        customers_df["return_rate"] = 0.0
        return customers_df
    
    try:
        # 1. Map return orders to customer_id using full_history_df
        # We need a mapping of order_id -> customer_id from ALL historical data
        id_map = _prepare_customer_identity(full_history_df)[["order_id", "customer_id"]].drop_duplicates()
        
        # 2. Extract order_id from returns
        ret_df = returns_df.copy()
        if "order_id" not in ret_df.columns:
            customers_df["return_count"] = 0
            customers_df["return_rate"] = 0.0
            return customers_df
            
        # 3. Merge returns with id_map to assign a customer_id to each return
        returns_mapped = ret_df.merge(id_map, on="order_id", how="inner")
        
        if returns_mapped.empty:
            customers_df["return_count"] = 0
            customers_df["return_rate"] = 0.0
            return customers_df
            
        # 4. Count returns per customer
        return_counts = returns_mapped.groupby("customer_id").size().reset_index(name="return_count")
        
        # 5. Merge with our target customers_df
        customers_df = customers_df.merge(return_counts, on="customer_id", how="left")
        customers_df["return_count"] = customers_df["return_count"].fillna(0).astype(int)
        
        # 6. Calculate return rate
        customers_df["return_rate"] = (customers_df["return_count"] / customers_df["total_orders"].replace(0, pd.NA)).fillna(0)
        
    except Exception as e:
        log_error(e, context="Return Rate Enrichment")
        customers_df["return_count"] = 0
        customers_df["return_rate"] = 0.0
        
    return customers_df



def get_favorite_products(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "item_name" not in df.columns:
        return pd.DataFrame(columns=["customer_id", "favorite_product"])
    counts = df.groupby(["customer_id", "item_name"]).size().reset_index(name="count")
    if counts.empty:
        return pd.DataFrame(columns=["customer_id", "favorite_product"])
    favorite = counts.loc[counts.groupby("customer_id")["count"].idxmax()].copy()
    favorite = favorite.rename(columns={"item_name": "favorite_product"})
    return favorite[["customer_id", "favorite_product"]]



def classify_rfm_segments(df: pd.DataFrame) -> pd.DataFrame:
    import polars as pl
    
    if df.empty:
        return df.copy()

    lz_df = pl.from_pandas(df).lazy()  # type: ignore
    
    lz_df = lz_df.with_columns(
        pl.when(pl.col("recency_days") > 180).then(pl.lit("Churned"))
        .when((pl.col("r_score") >= 4) & (pl.col("f_score") >= 4) & (pl.col("m_score") >= 4)).then(pl.lit("VIP"))
        .when((pl.col("f_score") <= 2) & (pl.col("r_score") >= 4)).then(pl.lit("New"))
        .when((pl.col("recency_days") > 60) & ((pl.col("f_score") >= 3) | (pl.col("m_score") >= 4))).then(pl.lit("At Risk"))
        .when((pl.col("r_score") >= 3) & (pl.col("f_score") >= 2)).then(pl.lit("Potential Loyalist"))
        .otherwise(pl.lit("Regular"))
        .alias("segment")
    )
    
    return lz_df.collect().to_pandas()


def _classify_without_rfm(row: pd.Series) -> str:
    recency = pd.to_numeric(str(row.get("recency_days", "")), errors="coerce")
    total_orders = pd.to_numeric(str(row.get("total_orders", "")), errors="coerce")
    total_revenue = pd.to_numeric(str(row.get("total_revenue", "")), errors="coerce")

    if pd.notna(recency) and recency > 180:
        return "Churned"
    if pd.notna(total_orders) and total_orders <= 1:
        return "New"
    if pd.notna(recency) and recency > 60:
        return "At Risk"
    if pd.notna(total_orders) and total_orders >= 5 and pd.notna(total_revenue) and total_revenue > 0:
        return "VIP"
    if pd.notna(total_orders) and total_orders >= 2:
        return "Potential Loyalist"
    return "Regular"



def get_customer_segments(df: pd.DataFrame) -> dict:
    if df.empty or "segment" not in df.columns:
        return {}
    grouped = {segment_name: df[df["segment"] == segment_name].copy() for segment_name in df["segment"].dropna().unique()}
    return dict(sorted(grouped.items(), key=lambda item: len(item[1]), reverse=True))



def search_customers(query: str, df: pd.DataFrame) -> pd.DataFrame:
    if not query or df.empty:
        return df
    query = query.lower().strip()

    text_match = (
        df["primary_name"].astype(str).str.lower().str.contains(query, na=False)
        | df["all_emails"].astype(str).str.lower().str.contains(query, na=False)
        | df["all_phones"].astype(str).str.contains(query, na=False)
    )
    segment_match = df["segment"].astype(str).str.lower().str.contains(query, na=False) if "segment" in df.columns else False
    rfm_match = df["rfm_score"].astype(str).str.contains(query.replace("rfm:", ""), na=False) if "rfm_score" in df.columns and (query.startswith("rfm:") or (query.isdigit() and len(query) == 3)) else False

    if isinstance(segment_match, pd.Series):
        return df[text_match | segment_match | rfm_match]
    return df[text_match | rfm_match]



def get_segment_summary(df: pd.DataFrame) -> pd.DataFrame:
    import polars as pl

    if df.empty or "segment" not in df.columns:
        return pd.DataFrame()
        
    lz_df = pl.from_pandas(df).lazy()  # type: ignore
    
    summary = lz_df.group_by("segment").agg([
        pl.col("customer_id").count().alias("Count"),
        pl.col("total_revenue").sum().alias("Total Revenue"),
        pl.col("total_revenue").mean().alias("Avg Revenue"),
        pl.col("total_orders").mean().alias("Avg Orders"),
        pl.col("avg_order_value").mean().alias("Avg AOV"),
        pl.col("recency_days").mean().alias("Avg Recency (days)"),
        pl.col("r_score").mean().alias("Avg R Score"),
        pl.col("f_score").mean().alias("Avg F Score"),
        pl.col("m_score").mean().alias("Avg M Score"),
    ]).collect().to_pandas()
    
    return summary.rename(columns={"segment": "Segment"}).sort_values("Total Revenue", ascending=False)


def generate_cohort_matrix(df: pd.DataFrame, period: str = 'M', metric: str = 'customers') -> pd.DataFrame:
    """
    Generates a retention cohort matrix.
    period: 'M' for monthly, 'W' for weekly.
    metric: 'customers' for unique customer count, 'revenue' for revenue sum.
    """
    import polars as pl

    if df.empty or 'order_date' not in df.columns:
        return pd.DataFrame()
        
    df = df.copy()
    
    # Ensure order_date is datetimelike before using Polars operations
    df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
    df = df.dropna(subset=['order_date'])
    
    # Need a consistent primary key for grouping
    if 'customer_id' not in df.columns:
        if 'customer_key' in df.columns:
            df['customer_id'] = df['customer_key']
        elif 'phone' in df.columns:
            df['customer_id'] = df['phone']
        else:
            df['customer_id'] = 'anon'
            
    # Use Lazy Polars for fast aggregation on large datasets
    lz_df = pl.from_pandas(df).lazy()  # type: ignore
    
    truncate_fmt = "1mo" if period == 'M' else "1w"
    
    lz_df = lz_df.with_columns(
        pl.col("order_date").dt.truncate(truncate_fmt).alias("order_period")
    ).with_columns(
        pl.col("order_period").min().over("customer_id").alias("cohort")
    )
    
    if period == 'M':
        lz_df = lz_df.with_columns(
            ((pl.col("order_period").dt.year() - pl.col("cohort").dt.year()) * 12 + 
             (pl.col("order_period").dt.month() - pl.col("cohort").dt.month())).alias("period_number")
        )
    else:
        lz_df = lz_df.with_columns(
            ((pl.col("order_period") - pl.col("cohort")).dt.total_days() // 7).cast(pl.Int32).alias("period_number")
        )
        
    if metric == 'revenue':
        revenue_col = "item_revenue" if "item_revenue" in df.columns else "order_total" if "order_total" in df.columns else None
        if revenue_col:
            cohort_group = lz_df.group_by(["cohort", "period_number"]).agg(
                pl.col(revenue_col).sum().alias("metric_value")
            ).collect().to_pandas()
        else:
            return pd.DataFrame()
    else:
        # Group and count unique customers
        cohort_group = lz_df.group_by(["cohort", "period_number"]).agg(
            pl.col("customer_id").n_unique().alias("metric_value")
        ).collect().to_pandas()
    
    if cohort_group.empty:
        return pd.DataFrame()
        
    # Format cohort back to Pandas Period for UI visualization compatibility
    cohort_group['cohort'] = pd.to_datetime(cohort_group['cohort']).dt.to_period(period)
    
    cohort_pivot = cohort_group.pivot_table(index='cohort', columns='period_number', values='metric_value')
    
    # Calculate percentage
    cohort_size = cohort_pivot.iloc[:, 0]
    retention_matrix = cohort_pivot.divide(cohort_size, axis=0) * 100
    
    return retention_matrix
