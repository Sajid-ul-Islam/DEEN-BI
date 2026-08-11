"""Meta Graph API v21.0 Service for Live Ad Account Insights & Campaign KPIs."""

from __future__ import annotations

import os
import requests
import pandas as pd
import numpy as np
import streamlit as st
from typing import Optional, Dict, Any
from BackEnd.core.logging_config import get_logger

logger = get_logger("meta_service")


def _get_secrets_dict() -> dict:
    """Safely fetch Streamlit secrets dictionary."""
    try:
        if hasattr(st, "secrets") and st.secrets:
            return dict(st.secrets)
    except Exception:
        pass

    secrets_path = os.path.join(".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
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


def get_meta_credentials() -> tuple[Optional[str], Optional[str]]:
    """Retrieves (access_token, ad_account_id) from secrets or environment."""
    sec = _get_secrets_dict()
    meta_sec = sec.get("meta", {}) if isinstance(sec.get("meta"), dict) else {}

    token = (
        sec.get("META_ACCESS_TOKEN")
        or meta_sec.get("access_token")
        or os.environ.get("META_ACCESS_TOKEN")
    )
    account_id = (
        sec.get("META_AD_ACCOUNT_ID")
        or meta_sec.get("ad_account_id")
        or os.environ.get("META_AD_ACCOUNT_ID")
    )

    if account_id and not str(account_id).startswith("act_"):
        account_id = f"act_{account_id}"

    return token, account_id


def is_meta_api_configured() -> bool:
    """Returns True if valid Meta access token and ad account ID are set."""
    token, account_id = get_meta_credentials()
    return bool(token and account_id)


def parse_meta_action_count(actions_list: list[dict], target_types: list[str]) -> int:
    """Parses total count for specific action types from Meta Graph API actions array."""
    if not isinstance(actions_list, list):
        return 0
    total = 0
    for item in actions_list:
        if isinstance(item, dict) and item.get("action_type") in target_types:
            try:
                total += int(float(item.get("value", 0)))
            except (ValueError, TypeError):
                pass
    return total


def parse_meta_action_value(action_values_list: list[dict], target_types: list[str]) -> float:
    """Parses total monetary value for specific action types from Meta action_values array."""
    if not isinstance(action_values_list, list):
        return 0.0
    total = 0.0
    for item in action_values_list:
        if isinstance(item, dict) and item.get("action_type") in target_types:
            try:
                total += float(item.get("value", 0.0))
            except (ValueError, TypeError):
                pass
    return total


def parse_meta_roas(roas_list: list[dict]) -> float:
    """Parses ROAS multiplier float from Meta purchase_roas array."""
    if not isinstance(roas_list, list):
        return 0.0
    for item in roas_list:
        if isinstance(item, dict) and item.get("action_type") in ["omni_purchase", "purchase"]:
            try:
                return float(item.get("value", 0.0))
            except (ValueError, TypeError):
                pass
    return 0.0


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_meta_campaign_insights(date_preset: str = "last_30d") -> pd.DataFrame:
    """
    Fetches campaign-level Insights from Meta Graph API v21.0.

    Returns DataFrame with columns:
    [campaign_id, campaign, source_medium, sessions, conversions, revenue,
     ad_spend, clicks, reach, impressions, ctr, cpc, roas, cac, net_profit]
    """
    token, account_id = get_meta_credentials()
    if not token or not account_id:
        logger.info("Meta credentials missing. Returning empty Insights DataFrame.")
        return pd.DataFrame()

    url = f"https://graph.facebook.com/v21.0/{account_id}/insights"
    params = {
        "access_token": token,
        "level": "campaign",
        "fields": "campaign_id,campaign_name,spend,impressions,reach,clicks,ctr,cpc,actions,action_values,purchase_roas",
        "date_preset": date_preset,
        "limit": 100,
    }

    try:
        response = requests.get(url, params=params, timeout=12)
        data = response.json()

        if "error" in data:
            err_msg = data["error"].get("message", "Unknown Graph API error")
            logger.warning(f"Meta Graph API error: {err_msg}")
            return pd.DataFrame()

        rows = []
        for item in data.get("data", []):
            camp_name = item.get("campaign_name", "Meta Campaign")
            camp_id = item.get("campaign_id", "")
            spend = float(item.get("spend", 0.0))
            impressions = int(item.get("impressions", 0))
            reach = int(item.get("reach", 0))
            clicks = int(item.get("clicks", 0))
            ctr = float(item.get("ctr", 0.0))
            cpc = float(item.get("cpc", 0.0))

            actions = item.get("actions", [])
            action_vals = item.get("action_values", [])
            roas_list = item.get("purchase_roas", [])

            # Parse purchase conversions & revenue
            purchase_types = ["omni_purchase", "purchase", "offsite_conversion.fb_pixel_purchase"]
            conversions = parse_meta_action_count(actions, purchase_types)
            revenue = parse_meta_action_value(action_vals, purchase_types)
            roas = parse_meta_roas(roas_list)

            if roas == 0.0 and spend > 0:
                roas = revenue / spend if spend > 0 else 0.0

            cac = (spend / conversions) if conversions > 0 else 0.0
            net_profit = revenue - spend - (revenue * 0.45)

            rows.append({
                "campaign_id": camp_id,
                "campaign": camp_name,
                "source_medium": "facebook / cpc",
                "sessions": clicks,
                "conversions": conversions,
                "revenue": revenue,
                "ad_spend": spend,
                "clicks": clicks,
                "reach": reach,
                "impressions": impressions,
                "ctr": ctr,
                "cpc": cpc,
                "roas": roas,
                "cac": cac,
                "net_profit": net_profit,
            })

        return pd.DataFrame(rows)

    except Exception as e:
        logger.error(f"Failed to fetch Meta Insights: {e}")
        return pd.DataFrame()
