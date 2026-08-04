import unittest
import pandas as pd
from BackEnd.core.categories import is_cashback_item, get_category_for_sales
from BackEnd.utils.sales_schema import estimate_line_revenue
from FrontEnd.pages.dashboard_lib.data_helpers import build_order_level_dataset, sum_order_level_revenue


class TestCashbackRevenueExclusion(unittest.TestCase):
    def test_is_cashback_item_detection(self):
        self.assertTrue(is_cashback_item("1000 Tk Cashback"))
        self.assertTrue(is_cashback_item("Cash Back Offer"))
        self.assertTrue(is_cashback_item("Tk 500 Cash-Back"))
        self.assertTrue(is_cashback_item("", category="Cashback"))
        self.assertFalse(is_cashback_item("Polo Shirt"))
        self.assertFalse(is_cashback_item("Denim Jeans"))

    def test_category_classification(self):
        self.assertEqual(get_category_for_sales("1000 Tk Cashback"), "Cashback")
        self.assertEqual(get_category_for_sales("Cash Back Voucher"), "Cashback")

    def test_estimate_line_revenue_zeroes_cashback(self):
        df = pd.DataFrame(
            {
                "order_id": ["101", "101"],
                "item_name": ["Polo Shirt", "500 Tk Cashback"],
                "qty": [1, 1],
                "item_revenue": [1200.0, 500.0],
            }
        )
        rev = estimate_line_revenue(df)
        self.assertEqual(list(rev), [1200.0, 0.0])

    def test_order_level_revenue_excludes_cashback(self):
        df = pd.DataFrame(
            {
                "order_id": ["101", "101", "102"],
                "order_date": ["2026-04-01", "2026-04-01", "2026-04-02"],
                "item_name": ["Polo Shirt", "500 Tk Cashback", "Denim Jeans"],
                "qty": [1, 1, 1],
                "item_revenue": [1200.0, 500.0, 1500.0],
            }
        )
        orders = build_order_level_dataset(df)
        total_rev = sum_order_level_revenue(df, orders)
        
        # Order 101: 1200 + 0 = 1200. Order 102: 1500. Total = 2700 (excluding 500 cashback)
        self.assertEqual(total_rev, 2700.0)


if __name__ == "__main__":
    unittest.main()
