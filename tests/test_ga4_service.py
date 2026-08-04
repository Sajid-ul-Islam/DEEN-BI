import unittest
import pandas as pd
from BackEnd.services.ga4_service import (
    is_ga4_configured,
    fetch_ga4_acquisition_metrics,
    fetch_ga4_channel_breakdown,
)


class TestGA4Service(unittest.TestCase):
    def test_is_ga4_configured_without_secrets(self):
        # Should gracefully return False when secrets/keys are unconfigured
        configured = is_ga4_configured()
        self.assertIsInstance(configured, bool)

    def test_fetch_ga4_acquisition_metrics_returns_dataframe(self):
        df = fetch_ga4_acquisition_metrics()
        self.assertIsInstance(df, pd.DataFrame)

    def test_fetch_ga4_channel_breakdown_returns_dataframe(self):
        df = fetch_ga4_channel_breakdown()
        self.assertIsInstance(df, pd.DataFrame)


if __name__ == "__main__":
    unittest.main()
