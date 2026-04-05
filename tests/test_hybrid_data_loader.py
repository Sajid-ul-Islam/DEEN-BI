import unittest
from unittest.mock import patch

import pandas as pd

from BackEnd.services import hybrid_data_loader


class _FakeWooService:
    def __init__(self):
        self.calls = []

    def fetch_all_historical_orders(self, after=None, before=None, status="any"):
        self.calls.append({"after": after, "before": before, "status": status})
        return pd.DataFrame(
            {
                "Order Number": ["1001"],
                "Order Date": ["2026-04-01 10:00:00"],
                "Customer Name": ["Jane"],
                "Qty": [1],
                "Item Name": ["Polo"],
                "Order Total Amount": [1200],
                "_source": ["woocommerce_api"],
            }
        )

    def get_stock_report(self):
        return pd.DataFrame(
            {
                "ID": [1],
                "Name": ["Polo"],
                "SKU": ["POLO-1"],
                "Stock Status": ["instock"],
                "Stock Quantity": ["7"],
                "Price": ["1200"],
            }
        )


class _FakeResponse:
    def __init__(self, csv_text: str):
        self.content = csv_text.encode("utf-8")

    def raise_for_status(self):
        return None


class TestHybridDataLoader(unittest.TestCase):
    def setUp(self):
        hybrid_data_loader.load_woocommerce_live_data.clear()
        hybrid_data_loader.load_woocommerce_stock_data.clear()
        hybrid_data_loader.load_live_stream_data.clear()
        hybrid_data_loader.load_comparison_data.clear()

    def test_woocommerce_loader_respects_selected_date_range(self):
        fake_service = _FakeWooService()

        with (
            patch.object(
                hybrid_data_loader.st,
                "secrets",
                {
                    "woocommerce": {
                        "store_url": "https://example.com",
                        "consumer_key": "ck_test",
                        "consumer_secret": "cs_test",
                    }
                },
            ),
            patch("BackEnd.services.woocommerce_service.WooCommerceService", return_value=fake_service),
        ):
            df = hybrid_data_loader.load_woocommerce_live_data(
                start_date="2026-04-01",
                end_date="2026-04-05",
            )

        self.assertFalse(df.empty)
        self.assertEqual(len(fake_service.calls), 1)
        self.assertEqual(fake_service.calls[0]["after"], "2026-04-01T00:00:00Z")
        self.assertEqual(fake_service.calls[0]["before"], "2026-04-05T23:59:59Z")

    def test_woocommerce_stock_loader_uses_api_and_normalizes_numbers(self):
        fake_service = _FakeWooService()

        with (
            patch.object(
                hybrid_data_loader.st,
                "secrets",
                {
                    "woocommerce": {
                        "store_url": "https://example.com",
                        "consumer_key": "ck_test",
                        "consumer_secret": "cs_test",
                    }
                },
            ),
            patch("BackEnd.services.woocommerce_service.WooCommerceService", return_value=fake_service),
        ):
            df = hybrid_data_loader.load_woocommerce_stock_data()

        self.assertEqual(len(df), 1)
        self.assertEqual(float(df.loc[0, "Stock Quantity"]), 7.0)
        self.assertEqual(float(df.loc[0, "Price"]), 1200.0)
        self.assertEqual(df.loc[0, "_source"], "woocommerce_stock_api")

    def test_live_stream_loader_uses_locked_stream_url(self):
        csv_text = "Order Number,Order Date,Customer Name,Qty,Item Name,Order Total Amount\n1001,2026-04-05 10:00:00,Jane,2,Polo,2400\n"

        with patch("BackEnd.services.hybrid_data_loader.requests.get", return_value=_FakeResponse(csv_text)) as mock_get:
            df = hybrid_data_loader.load_live_stream_data()

        self.assertFalse(df.empty)
        self.assertEqual(mock_get.call_args.args[0], hybrid_data_loader.LIVE_STREAM_URL)

    def test_comparison_loader_uses_locked_comparison_url(self):
        csv_text = "Order Number,Order Date,Customer Name,Qty,Item Name,Order Total Amount\n1000,2026-04-04 10:00:00,Jane,1,Polo,1200\n"

        with patch("BackEnd.services.hybrid_data_loader.requests.get", return_value=_FakeResponse(csv_text)) as mock_get:
            df = hybrid_data_loader.load_comparison_data()

        self.assertFalse(df.empty)
        self.assertEqual(mock_get.call_args.args[0], hybrid_data_loader.COMPARISON_SHEET_URL)


if __name__ == "__main__":
    unittest.main()
