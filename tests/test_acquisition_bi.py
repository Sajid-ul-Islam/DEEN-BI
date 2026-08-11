import pytest
import pandas as pd
from BackEnd.services.ad_spend_service import calculate_campaign_unit_economics
from BackEnd.utils.sales_schema import ensure_sales_schema


def test_ad_spend_service_calculations():
    df = pd.DataFrame([
        {"campaign": "Summer_Meta", "source_medium": "facebook / cpc", "sessions": 1000, "conversions": 50, "revenue": 100000.0, "engagement_rate": 60.0},
        {"campaign": "Google_Brand", "source_medium": "google / cpc", "sessions": 500, "conversions": 40, "revenue": 80000.0, "engagement_rate": 75.0},
        {"campaign": "Organic_SEO", "source_medium": "google / organic", "sessions": 300, "conversions": 10, "revenue": 20000.0, "engagement_rate": 70.0},
    ])

    res = calculate_campaign_unit_economics(df)

    assert not res.empty
    assert "ad_spend" in res.columns
    assert "roas" in res.columns
    assert "cac" in res.columns
    assert "cpc" in res.columns
    assert "net_profit" in res.columns

    # Organic search should have 0 ad spend
    organic_row = res[res["campaign"] == "Organic_SEO"].iloc[0]
    assert organic_row["ad_spend"] == 0.0
    assert organic_row["roas"] == 0.0

    # Paid Meta should have positive spend and ROAS
    meta_row = res[res["campaign"] == "Summer_Meta"].iloc[0]
    assert meta_row["ad_spend"] > 0
    assert meta_row["roas"] > 0
    assert meta_row["cac"] > 0


def test_sales_schema_utm_aliases():
    raw_df = pd.DataFrame([
        {"order_id": "101", "order_date": "2026-08-01", "order_total": "1500", "_utm_source": "facebook", "_utm_medium": "cpc", "_utm_campaign": "summer_sale"}
    ])

    normalized = ensure_sales_schema(raw_df)

    assert "utm_source" in normalized.columns
    assert "utm_medium" in normalized.columns
    assert "utm_campaign" in normalized.columns
    assert normalized.iloc[0]["utm_source"] == "facebook"
    assert normalized.iloc[0]["utm_medium"] == "cpc"
    assert normalized.iloc[0]["utm_campaign"] == "summer_sale"
