import pytest
import pandas as pd
from BackEnd.services.meta_service import (
    is_meta_api_configured,
    get_meta_credentials,
    parse_meta_action_count,
    parse_meta_action_value,
    parse_meta_roas,
    fetch_meta_campaign_insights,
)


def test_meta_credentials_detection():
    token, account_id = get_meta_credentials()
    assert token is not None
    assert account_id == "act_3397888253858911"
    assert is_meta_api_configured() is True


def test_parse_meta_actions():
    actions = [
        {"action_type": "link_click", "value": "150"},
        {"action_type": "omni_purchase", "value": "12"},
        {"action_type": "page_engagement", "value": "450"},
    ]
    conversions = parse_meta_action_count(actions, ["omni_purchase", "purchase"])
    assert conversions == 12

    action_values = [
        {"action_type": "omni_purchase", "value": "24000.50"},
        {"action_type": "add_to_cart", "value": "5000.00"},
    ]
    revenue = parse_meta_action_value(action_values, ["omni_purchase", "purchase"])
    assert revenue == 24000.50

    roas_data = [
        {"action_type": "omni_purchase", "value": "3.45"}
    ]
    roas = parse_meta_roas(roas_data)
    assert roas == 3.45


def test_fetch_meta_insights_graceful_fallback():
    df = fetch_meta_campaign_insights("last_30d")
    assert isinstance(df, pd.DataFrame)
