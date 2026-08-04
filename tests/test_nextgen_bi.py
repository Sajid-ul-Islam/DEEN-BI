import unittest
import pandas as pd
from BackEnd.services.variant_analytics import analyze_variant_velocity
from BackEnd.services.profitability_engine import calculate_contribution_margin
from BackEnd.services.affinity_engine import MarketBasketEngine
from BackEnd.services.cohort_analytics import calculate_cohort_ltv
from BackEnd.services.ga4_service import is_ga4_configured, fetch_ga4_channel_breakdown


class TestNextGenBISuite(unittest.TestCase):
    def setUp(self):
        self.df_sales = pd.DataFrame({
            "order_id": ["1001", "1001", "1002", "1003", "1003"],
            "order_date": ["2026-04-01 10:00:00", "2026-04-01 10:00:00", "2026-04-02 11:00:00", "2026-04-05 12:00:00", "2026-04-05 12:00:00"],
            "item_name": ["Polo Shirt - Blue - L", "Twill Chino - Black - 32", "Polo Shirt - Blue - M", "Panjabi - White - L", "1000 Tk Cashback"],
            "Category": ["Polo Shirt", "Twill", "Polo Shirt", "Panjabi", "Cashback"],
            "qty": [1, 1, 1, 1, 1],
            "item_revenue": [1200.0, 1800.0, 1200.0, 2500.0, 1000.0],
            "order_total": [3000.0, 3000.0, 1200.0, 3500.0, 3500.0],
            "customer_key": ["cust_1", "cust_1", "cust_2", "cust_1", "cust_1"],
            "order_status": ["completed", "completed", "completed", "cancelled", "cancelled"],
            "state": ["Dhaka", "Dhaka", "Chittagong", "Sylhet", "Sylhet"]
        })

    def test_variant_analytics(self):
        res = analyze_variant_velocity(self.df_sales)
        self.assertIn("variant_df", res)
        self.assertIn("size_summary", res)
        self.assertIn("color_summary", res)
        self.assertFalse(res["variant_df"].empty)

    def test_contribution_margin_pnl(self):
        pnl = calculate_contribution_margin(self.df_sales, cogs_margin=0.40)
        self.assertGreater(pnl["gross_sales"], 0)
        self.assertIn("cm1", pnl)
        self.assertIn("cm2", pnl)
        self.assertIn("product_profitability", pnl)

    def test_market_basket_associations(self):
        engine = MarketBasketEngine(self.df_sales)
        rules = engine.get_associations(min_support=0.001, min_lift=0.5)
        self.assertIsInstance(rules, pd.DataFrame)

    def test_cohort_ltv_calculation(self):
        res = calculate_cohort_ltv(self.df_sales)
        self.assertIn("cohort_matrix", res)
        self.assertIn("churn_alerts", res)
        self.assertFalse(res["cohort_matrix"].empty)

    def test_ga4_service_integration(self):
        configured = is_ga4_configured()
        self.assertTrue(configured)  # GA4 credentials are configured in secrets.toml
        breakdown = fetch_ga4_channel_breakdown()
        self.assertIsInstance(breakdown, pd.DataFrame)


if __name__ == "__main__":
    unittest.main()
