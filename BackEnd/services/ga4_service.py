"""Google Analytics 4 (GA4) API integration service for Traffic & User Acquisition."""

from __future__ import annotations

import os
import pandas as pd
import streamlit as st
from typing import Optional
from BackEnd.core.logging_config import get_logger

logger = get_logger("ga4_service")

# --- Graceful import for Google Analytics Data API ---
GA4_API_AVAILABLE = False
try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
    from google.oauth2 import service_account
    GA4_API_AVAILABLE = True
except ImportError:
    GA4_API_AVAILABLE = False
    logger.info("google-analytics-data SDK not installed. GA4 live API disabled.")


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


def _get_ga4_property_id(sec: dict) -> str | None:
    """Extract GA4 property ID from root, llm section, ga4 section, or environment."""
    pid = (
        sec.get("GA4_PROPERTY_ID")
        or sec.get("llm", {}).get("GA4_PROPERTY_ID")
        or sec.get("ga4", {}).get("property_id")
        or os.environ.get("GA4_PROPERTY_ID")
    )
    return str(pid) if pid else None


def is_ga4_configured() -> bool:
    """Returns True if GA4 credentials and property ID are present in secrets or env."""
    if not GA4_API_AVAILABLE:
        return False
        
    sec = _get_secrets_dict()
    has_property = bool(_get_ga4_property_id(sec))
    has_credentials = "gcp_service_account" in sec or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
    return bool(has_property and has_credentials)


def _get_ga4_credentials_and_property() -> tuple[Optional[object], Optional[str]]:
    """Retrieve Google Cloud service account credentials and GA4 property ID."""
    if not GA4_API_AVAILABLE:
        return None, None

    sec = _get_secrets_dict()
    property_id = _get_ga4_property_id(sec)
    if not property_id:
        return None, None

    if not str(property_id).startswith("properties/"):
        property_id = f"properties/{property_id}"


    credentials = None
    if "gcp_service_account" in sec:
        try:
            creds_dict = dict(sec["gcp_service_account"])
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
        except Exception as e:
            logger.error(f"Failed to parse gcp_service_account from secrets: {e}")

    elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            credentials = service_account.Credentials.from_service_account_file(
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
            )
        except Exception as e:
            logger.error(f"Failed to load GOOGLE_APPLICATION_CREDENTIALS file: {e}")

    return credentials, property_id



@st.cache_data(ttl=1800, show_spinner=False)
def fetch_ga4_acquisition_metrics(start_date: str = "30daysAgo", end_date: str = "today") -> pd.DataFrame:
    """Fetch traffic and acquisition performance metrics from GA4 REST API.
    
    Returns a DataFrame with columns:
    [source_medium, date, device, active_users, sessions, conversions, revenue, conversion_rate]
    """
    credentials, property_id = _get_ga4_credentials_and_property()
    if not credentials or not property_id:
        logger.warning("GA4 API credentials or property ID missing. Returning empty DataFrame.")
        return pd.DataFrame()

    try:
        client = BetaAnalyticsDataClient(credentials=credentials)

        request = RunReportRequest(
            property=property_id,
            dimensions=[
                Dimension(name="sessionSourceMedium"),
                Dimension(name="date"),
                Dimension(name="deviceCategory"),
            ],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="sessions"),
                Metric(name="conversions"),
                Metric(name="totalRevenue"),
                Metric(name="userConversionRate"),
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        )

        response = client.run_report(request)

        rows = []
        for row in response.rows:
            rows.append({
                "source_medium": row.dimension_values[0].value,
                "date": pd.to_datetime(row.dimension_values[1].value, format="%Y%m%d", errors="coerce"),
                "device": row.dimension_values[2].value.title(),
                "active_users": int(row.metric_values[0].value or 0),
                "sessions": int(row.metric_values[1].value or 0),
                "conversions": int(row.metric_values[2].value or 0),
                "revenue": float(row.metric_values[3].value or 0.0),
                "conversion_rate": float(row.metric_values[4].value or 0.0) * 100.0,
            })

        df = pd.DataFrame(rows)
        logger.info(f"Successfully fetched {len(df)} GA4 acquisition records.")
        return df

    except Exception as exc:
        logger.error(f"Error executing GA4 API query: {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_ga4_channel_breakdown(start_date: str = "30daysAgo", end_date: str = "today") -> pd.DataFrame:
    """Fetch channel attribution breakdown from GA4 REST API."""
    df = fetch_ga4_acquisition_metrics(start_date=start_date, end_date=end_date)
    if df.empty:
        return pd.DataFrame()

    summary = df.groupby("source_medium", as_index=False).agg(
        sessions=("sessions", "sum"),
        active_users=("active_users", "sum"),
        conversions=("conversions", "sum"),
        revenue=("revenue", "sum"),
    )
    summary["conversion_rate"] = (summary["conversions"] / summary["sessions"].replace(0, 1)) * 100.0
    return summary.sort_values("sessions", ascending=False).reset_index(drop=True)
