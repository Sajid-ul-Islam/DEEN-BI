"""Ad Spend & Campaign Unit Economics Service (CAC, ROAS, CPC, Net Profit Impact)."""

from __future__ import annotations

import os
import pandas as pd
import numpy as np
import streamlit as st
from typing import Optional
from BackEnd.core.logging_config import get_logger

logger = get_logger("ad_spend_service")


def _get_secrets_dict() -> dict:
    """Safely fetch Streamlit secrets dictionary."""
    try:
        if hasattr(st, "secrets") and st.secrets:
            return dict(st.secrets)
    except Exception:
        pass
    return {}


def is_meta_ads_configured() -> bool:
    """Check if Meta Ad Account API credentials exist in secrets or environment."""
    sec = _get_secrets_dict()
    token = sec.get("META_ACCESS_TOKEN") or os.environ.get("META_ACCESS_TOKEN")
    account_id = sec.get("META_AD_ACCOUNT_ID") or os.environ.get("META_AD_ACCOUNT_ID")
    return bool(token and account_id)


def calculate_campaign_unit_economics(campaign_df: pd.DataFrame) -> pd.DataFrame:
    """
    Enhances a campaign DataFrame (containing campaign, source_medium, sessions, conversions, revenue)
    with ad_spend, cpc, roas, cac, and profit_impact columns.
    """
    if campaign_df.empty:
        return pd.DataFrame(columns=[
            "campaign", "source_medium", "sessions", "conversions", "revenue",
            "engagement_rate", "ad_spend", "clicks", "cpc", "roas", "cac", "net_profit"
        ])

    df = campaign_df.copy()

    # Ensure numeric columns
    for col in ["sessions", "conversions", "revenue", "engagement_rate"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    # Model or calculate ad spend based on source / medium
    if "ad_spend" not in df.columns:
        spends = []
        for _, row in df.iterrows():
            src = str(row.get("source_medium", "")).lower()
            rev = float(row.get("revenue", 0))
            sess = int(row.get("sessions", 0))
            is_unpaid = "organic" in src or "direct" in src or "referral" in src
            is_paid = "cpc" in src or "paid" in src or "facebook" in src or "instagram" in src or "meta" in src or "ads" in src

            if is_unpaid and not is_paid:
                estimated_spend = 0.0
            elif is_paid:
                # Benchmark 25% - 40% ad spend ratio for paid campaigns
                estimated_spend = max(rev * 0.32, sess * 8.5)
            elif "email" in src or "newsletter" in src:
                estimated_spend = max(rev * 0.05, 500)
            else:
                # Organic / Direct has zero paid ad spend
                estimated_spend = 0.0
            spends.append(round(estimated_spend, 2))
        df["ad_spend"] = spends

    # Clicks baseline from sessions
    df["clicks"] = df["sessions"].apply(lambda s: int(s * 1.05))

    # Calculate CPC: ad_spend / clicks
    df["cpc"] = np.where(df["clicks"] > 0, df["ad_spend"] / df["clicks"], 0.0)

    # Calculate ROAS: revenue / ad_spend (0 if no spend)
    df["roas"] = np.where(df["ad_spend"] > 0, df["revenue"] / df["ad_spend"], 0.0)

    # Calculate CAC: ad_spend / conversions
    df["cac"] = np.where(df["conversions"] > 0, df["ad_spend"] / df["conversions"], 0.0)

    # Calculate Net Profit Impact: revenue - ad_spend - estimated COGS (45%)
    df["net_profit"] = df["revenue"] - df["ad_spend"] - (df["revenue"] * 0.45)

    return df
