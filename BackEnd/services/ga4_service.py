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


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_ga4_aarrr_funnel_metrics(start_date: str = "30daysAgo", end_date: str = "today") -> dict:
    """Fetch GA4 metrics aggregated for AARRR Pirate Funnel stages."""
    credentials, property_id = _get_ga4_credentials_and_property()
    if not credentials or not property_id:
        return {}

    try:
        client = BetaAnalyticsDataClient(credentials=credentials)

        request = RunReportRequest(
            property=property_id,
            metrics=[
                Metric(name="sessions"),
                Metric(name="activeUsers"),
                Metric(name="newUsers"),
                Metric(name="engagedSessions"),
                Metric(name="conversions"),
                Metric(name="totalRevenue"),
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        )

        response = client.run_report(request)
        if not response.rows:
            return {}

        row = response.rows[0]
        sessions = int(row.metric_values[0].value or 0)
        active_users = int(row.metric_values[1].value or 0)
        new_users = int(row.metric_values[2].value or 0)
        engaged_sessions = int(row.metric_values[3].value or 0)
        conversions = int(row.metric_values[4].value or 0)
        revenue = float(row.metric_values[5].value or 0.0)

        returning_users = max(0, active_users - new_users)

        return {
            "acquisition_sessions": sessions,
            "acquisition_users": active_users,
            "activation_engaged_sessions": engaged_sessions,
            "retention_returning_users": returning_users,
            "retention_new_users": new_users,
            "revenue_conversions": conversions,
            "revenue_amount": revenue,
        }
    except Exception as exc:
        logger.error(f"Error fetching GA4 AARRR funnel metrics: {exc}")
        return {}


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_ga4_user_engagement_metrics(start_date: str = "30daysAgo", end_date: str = "today") -> dict:
    """Fetch global property user engagement metrics: engagementRate, bounceRate, averageSessionDuration, screenPageViews, eventCount."""
    credentials, property_id = _get_ga4_credentials_and_property()
    if not credentials or not property_id:
        return {}

    try:
        client = BetaAnalyticsDataClient(credentials=credentials)

        request = RunReportRequest(
            property=property_id,
            metrics=[
                Metric(name="engagementRate"),
                Metric(name="bounceRate"),
                Metric(name="averageSessionDuration"),
                Metric(name="screenPageViews"),
                Metric(name="eventCount"),
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        )

        response = client.run_report(request)
        if not response.rows:
            return {}

        row = response.rows[0]
        return {
            "engagement_rate": float(row.metric_values[0].value or 0.0) * 100.0,
            "bounce_rate": float(row.metric_values[1].value or 0.0) * 100.0,
            "avg_session_duration": float(row.metric_values[2].value or 0.0),
            "page_views": int(row.metric_values[3].value or 0),
            "event_count": int(row.metric_values[4].value or 0),
        }
    except Exception as exc:
        logger.error(f"Error fetching GA4 engagement metrics: {exc}")
        return {}


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_ga4_landing_pages(start_date: str = "30daysAgo", end_date: str = "today") -> pd.DataFrame:
    """Fetch landing page performance metrics from GA4."""
    credentials, property_id = _get_ga4_credentials_and_property()
    if not credentials or not property_id:
        return pd.DataFrame()

    try:
        client = BetaAnalyticsDataClient(credentials=credentials)

        request = RunReportRequest(
            property=property_id,
            dimensions=[
                Dimension(name="landingPage"),
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="activeUsers"),
                Metric(name="engagementRate"),
                Metric(name="conversions"),
                Metric(name="totalRevenue"),
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            limit=25,
        )

        response = client.run_report(request)
        rows = []
        for row in response.rows:
            rows.append({
                "landing_page": row.dimension_values[0].value,
                "sessions": int(row.metric_values[0].value or 0),
                "active_users": int(row.metric_values[1].value or 0),
                "engagement_rate": float(row.metric_values[2].value or 0.0) * 100.0,
                "conversions": int(row.metric_values[3].value or 0),
                "revenue": float(row.metric_values[4].value or 0.0),
            })

        df = pd.DataFrame(rows)
        return df.sort_values("sessions", ascending=False).reset_index(drop=True)
    except Exception as exc:
        logger.error(f"Error fetching GA4 landing pages: {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_ga4_geo_metrics(start_date: str = "30daysAgo", end_date: str = "today") -> pd.DataFrame:
    """Fetch geographic location breakdown (city and country) from GA4."""
    credentials, property_id = _get_ga4_credentials_and_property()
    if not credentials or not property_id:
        return pd.DataFrame()

    try:
        client = BetaAnalyticsDataClient(credentials=credentials)

        request = RunReportRequest(
            property=property_id,
            dimensions=[
                Dimension(name="country"),
                Dimension(name="city"),
            ],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="sessions"),
                Metric(name="conversions"),
                Metric(name="totalRevenue"),
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            limit=30,
        )

        response = client.run_report(request)
        rows = []
        for row in response.rows:
            city_val = row.dimension_values[1].value
            if city_val in ("(not set)", "not set", ""):
                city_val = "Unknown / Direct"
            rows.append({
                "country": row.dimension_values[0].value,
                "city": city_val,
                "active_users": int(row.metric_values[0].value or 0),
                "sessions": int(row.metric_values[1].value or 0),
                "conversions": int(row.metric_values[2].value or 0),
                "revenue": float(row.metric_values[3].value or 0.0),
            })

        df = pd.DataFrame(rows)
        return df.sort_values("sessions", ascending=False).reset_index(drop=True)
    except Exception as exc:
        logger.error(f"Error fetching GA4 geo metrics: {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_ga4_campaign_performance(start_date: str = "30daysAgo", end_date: str = "today") -> pd.DataFrame:
    """Fetch marketing campaign performance breakdown from GA4."""
    credentials, property_id = _get_ga4_credentials_and_property()
    if not credentials or not property_id:
        return pd.DataFrame()

    try:
        client = BetaAnalyticsDataClient(credentials=credentials)

        request = RunReportRequest(
            property=property_id,
            dimensions=[
                Dimension(name="sessionCampaignName"),
                Dimension(name="sessionSourceMedium"),
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="conversions"),
                Metric(name="totalRevenue"),
                Metric(name="engagementRate"),
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            limit=25,
        )

        response = client.run_report(request)
        rows = []
        for row in response.rows:
            camp = row.dimension_values[0].value
            if camp in ("(not set)", "(direct)", "(referral)", ""):
                camp = "Unassigned / Direct"
            rows.append({
                "campaign": camp,
                "source_medium": row.dimension_values[1].value,
                "sessions": int(row.metric_values[0].value or 0),
                "conversions": int(row.metric_values[1].value or 0),
                "revenue": float(row.metric_values[2].value or 0.0),
                "engagement_rate": float(row.metric_values[3].value or 0.0) * 100.0,
            })

        df = pd.DataFrame(rows)
        return df.sort_values("sessions", ascending=False).reset_index(drop=True)
    except Exception as exc:
        logger.error(f"Error fetching GA4 campaign performance: {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_ga4_ecommerce_events(start_date: str = "30daysAgo", end_date: str = "today") -> pd.DataFrame:
    """Fetch GA4 e-commerce funnel events: view_item, add_to_cart, begin_checkout, purchase."""
    credentials, property_id = _get_ga4_credentials_and_property()
    if not credentials or not property_id:
        return pd.DataFrame()

    try:
        client = BetaAnalyticsDataClient(credentials=credentials)

        request = RunReportRequest(
            property=property_id,
            dimensions=[
                Dimension(name="eventName"),
            ],
            metrics=[
                Metric(name="eventCount"),
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        )

        response = client.run_report(request)
        rows = []
        target_events = {"view_item", "add_to_cart", "begin_checkout", "purchase"}
        for row in response.rows:
            ename = row.dimension_values[0].value
            if ename in target_events:
                rows.append({
                    "event_name": ename,
                    "event_count": int(row.metric_values[0].value or 0),
                })

        df = pd.DataFrame(rows)
        return df
    except Exception as exc:
        logger.error(f"Error fetching GA4 e-commerce events: {exc}")
        return pd.DataFrame()


