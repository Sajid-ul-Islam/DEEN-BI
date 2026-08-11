"""Ad Spend & Campaign Unit Economics Service (CAC, ROAS, CPC, Net Profit Impact)."""

from __future__ import annotations

import os
import pandas as pd
import numpy as np
import streamlit as st
from typing import Optional
from BackEnd.core.logging_config import get_logger

logger = get_logger("ad_spend_service")


from pathlib import Path


def _get_secrets_dict() -> dict:
    """Safely fetch Streamlit secrets dictionary, with local fallback for non-Streamlit threads/CLI."""
    try:
        if hasattr(st, "secrets") and st.secrets:
            return dict(st.secrets)
    except Exception:
        pass

    secrets_path = Path(".streamlit/secrets.toml")
    if secrets_path.exists():
        try:
            import tomllib
            with open(secrets_path, "rb") as f:
                return tomllib.load(f)
        except Exception:
            try:
                import toml
                return toml.load(secrets_path)
            except Exception:
                pass
    return {}


def is_meta_ads_configured() -> bool:
    """Check if Meta Ad Account API credentials exist in secrets or environment."""
    sec = _get_secrets_dict()
    meta_sec = sec.get("meta", {}) if isinstance(sec.get("meta"), dict) else {}
    token = sec.get("META_ACCESS_TOKEN") or meta_sec.get("access_token") or os.environ.get("META_ACCESS_TOKEN")
    account_id = sec.get("META_AD_ACCOUNT_ID") or meta_sec.get("ad_account_id") or os.environ.get("META_AD_ACCOUNT_ID")
    return bool(token and account_id)


def calculate_campaign_unit_economics(campaign_df: pd.DataFrame) -> pd.DataFrame:
    """
    Enhances a campaign DataFrame (containing campaign, source_medium, sessions, conversions, revenue)
    with ad_spend, cpc, roas, cac, and profit_impact columns.
    Merges live Meta Graph API Insights when available.
    """
    from BackEnd.services.meta_service import is_meta_api_configured, fetch_meta_campaign_insights

    # Fetch live Meta Insights if configured
    meta_df = fetch_meta_campaign_insights("last_30d") if is_meta_api_configured() else pd.DataFrame()

    if campaign_df.empty:
        if not meta_df.empty:
            return meta_df
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

    # If live Meta Insights are available, map live spend and ROAS onto Meta campaigns
    if not meta_df.empty:
        meta_map = meta_df.set_index("campaign").to_dict("index")
        for idx, row in df.iterrows():
            c_name = str(row.get("campaign", ""))
            src = str(row.get("source_medium", "")).lower()

            if c_name in meta_map:
                m_info = meta_map[c_name]
                df.at[idx, "ad_spend"] = m_info.get("ad_spend", 0.0)
                df.at[idx, "clicks"] = m_info.get("clicks", int(row.get("sessions", 0)))
                df.at[idx, "cpc"] = m_info.get("cpc", 0.0)
                df.at[idx, "roas"] = m_info.get("roas", 0.0)
                df.at[idx, "cac"] = m_info.get("cac", 0.0)
                df.at[idx, "net_profit"] = m_info.get("net_profit", 0.0)
                if "reach" in m_info:
                    df.at[idx, "reach"] = m_info.get("reach", 0)
                if "impressions" in m_info:
                    df.at[idx, "impressions"] = m_info.get("impressions", 0)
            elif "facebook" in src or "instagram" in src or "meta" in src:
                # Top Meta campaign match fallback from meta_df
                top_meta = meta_df.iloc[0]
                df.at[idx, "ad_spend"] = float(top_meta.get("ad_spend", 0.0))
                df.at[idx, "roas"] = float(top_meta.get("roas", 0.0))
                df.at[idx, "cac"] = float(top_meta.get("cac", 0.0))

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

    # Calculate CVR: (conversions / sessions) * 100
    df["cvr"] = np.where(df["sessions"] > 0, (df["conversions"] / df["sessions"]) * 100.0, 0.0)
    df["cvr"] = df["cvr"].clip(lower=0.0, upper=100.0)

    # Calculate Net Profit Impact: revenue - ad_spend - estimated COGS (45%)
    df["net_profit"] = df["revenue"] - df["ad_spend"] - (df["revenue"] * 0.45)

    return df
