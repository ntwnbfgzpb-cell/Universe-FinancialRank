import unittest
from decimal import Decimal as D

from desktop.core.transform import cumulative_to_quarters, core_fcf, inventory_turnover, revenue_growth


class TransformTests(unittest.TestCase):
    def test_cumulative_to_quarter_including_q4(self):
        self.assertEqual(cumulative_to_quarters({1:10,2:25,3:45,4:70}),
                         {1:D("10"),2:D("15"),3:D("20"),4:D("25")})

    def test_missing_prior_quarter_does_not_invent_zero(self):
        self.assertEqual(cumulative_to_quarters({1:10,3:45})[3], None)

    def test_core_fcf_normalizes_cash_outflow_sign(self):
        self.assertEqual(core_fcf(100, -20, 5), D("75"))

    def test_zero_inventory_is_null(self):
        self.assertIsNone(inventory_turnover(100, 0, 0))

    def test_revenue_growth_zero_base_is_null(self):
        self.assertIsNone(revenue_growth(100, 0))


if __name__ == "__main__":
    unittest.main()
