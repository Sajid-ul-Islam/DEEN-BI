import unittest

import pandas as pd

from BackEnd.services.returns_tracker import calculate_net_sales_metrics


class TestReturnsTrackerFinancials(unittest.TestCase):
    def test_financial_metrics_use_item_match_and_partial_amount(self):
        sales_df = pd.DataFrame(
            {
                "order_id": ["1001", "1001", "1002"],
                "order_date": ["2026-04-01 10:00:00", "2026-04-01 10:00:00", "2026-04-02 11:00:00"],
                "item_name": ["Polo Shirt", "Denim Pant", "Oxford Shirt"],
                "sku": ["POLO-01", "DENIM-01", "OXF-01"],
                "qty": [1, 1, 1],
                "item_revenue": [400.0, 600.0, 800.0],
                "order_total": [1000.0, 1000.0, 800.0],
            }
        )

        returns_df = pd.DataFrame(
            {
                "order_id": ["1001", "1002"],
                "order_id_raw": ["1001", "1002"],
                "date": pd.to_datetime(["2026-04-03", "2026-04-04"]),
                "issue_type": ["Paid Return", "Partial"],
                "return_reason": ["Size Issue", "Changed Mind"],
                "partial_amount": [0.0, 250.0],
                "returned_items": [
                    [{"name": "Polo Shirt", "sku": "POLO-01", "qty": 1}],
                    [{"name": "Oxford Shirt", "sku": "OXF-01", "qty": 1}],
                ],
            }
        )

        metrics = calculate_net_sales_metrics(returns_df, sales_df=sales_df)

        self.assertEqual(metrics["gross_sales"], 1800.0)
        self.assertEqual(metrics["full_return_loss"], 400.0)
        self.assertEqual(metrics["partial_loss"], 250.0)
        self.assertEqual(metrics["total_loss"], 650.0)
        self.assertEqual(metrics["net_sales"], 1150.0)
        self.assertEqual(metrics["matched_returned_items"], 2)
        self.assertEqual(metrics["estimated_returned_items"], 0)
        self.assertEqual(metrics["attribution_confidence_pct"], 100.0)

    def test_full_return_falls_back_to_order_value_when_item_match_missing(self):
        sales_df = pd.DataFrame(
            {
                "order_id": ["2001", "2001"],
                "order_date": ["2026-04-05 10:00:00", "2026-04-05 10:00:00"],
                "item_name": ["Linen Shirt", "Chino Pant"],
                "sku": ["LINEN-01", "CHINO-01"],
                "qty": [1, 1],
                "item_revenue": [500.0, 700.0],
                "order_total": [1200.0, 1200.0],
            }
        )
        returns_df = pd.DataFrame(
            {
                "order_id": ["2001"],
                "order_id_raw": ["2001"],
                "date": pd.to_datetime(["2026-04-06"]),
                "issue_type": ["Non Paid Return"],
                "return_reason": ["Unknown"],
                "partial_amount": [0.0],
                "returned_items": [[{"name": "Unknown Product", "sku": "N/A", "qty": 1}]],
            }
        )

        metrics = calculate_net_sales_metrics(returns_df, sales_df=sales_df)

        self.assertEqual(metrics["full_return_loss"], 1200.0)
        self.assertEqual(metrics["unattributed_issue_orders"], 0)
        self.assertEqual(metrics["estimated_returned_items"], 1)

    def test_daily_financials_include_sales_and_return_dates(self):
        sales_df = pd.DataFrame(
            {
                "order_id": ["3001", "3002"],
                "order_date": ["2026-04-07 09:00:00", "2026-04-08 09:00:00"],
                "item_name": ["Basic Tee", "Cargo Pant"],
                "sku": ["TEE-01", "CARGO-01"],
                "qty": [1, 1],
                "item_revenue": [300.0, 900.0],
                "order_total": [300.0, 900.0],
            }
        )
        returns_df = pd.DataFrame(
            {
                "order_id": ["3002"],
                "order_id_raw": ["3002"],
                "date": pd.to_datetime(["2026-04-09"]),
                "issue_type": ["Paid Return"],
                "return_reason": ["Quality Issue"],
                "partial_amount": [0.0],
                "returned_items": [[{"name": "Cargo Pant", "sku": "CARGO-01", "qty": 1}]],
            }
        )

        metrics = calculate_net_sales_metrics(returns_df, sales_df=sales_df)
        daily = metrics["daily_financials"].copy()

        self.assertEqual(len(daily), 3)
        self.assertEqual(float(daily.loc[pd.to_datetime(daily["date"]).dt.date == pd.to_datetime("2026-04-09").date(), "total_loss"].iloc[0]), 900.0)
        self.assertEqual(float(daily.loc[pd.to_datetime(daily["date"]).dt.date == pd.to_datetime("2026-04-08").date(), "gross_sales"].iloc[0]), 900.0)


if __name__ == "__main__":
    unittest.main()
