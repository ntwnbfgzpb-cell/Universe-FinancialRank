import unittest
from decimal import Decimal

from desktop.core.scoring import (
    GradeResult, RankingEngine, eps_profitability, free_cash_flow, inventory_turnover,
    net_profit_growth, operating_margin, overall, revenue_growth,
)


class BoundaryTests(unittest.TestCase):
    def test_eps_boundaries(self):
        self.assertEqual(eps_profitability([1,1,1,2]).grade, "A")
        self.assertEqual(eps_profitability([1,1,1,0]).grade, "A")
        self.assertEqual(eps_profitability([0,0,0,1]).grade, "BB")
        self.assertEqual(eps_profitability([0,0,0,0]).grade, "B")
        self.assertEqual(eps_profitability([2,2,2,-1]).grade, "C")

    def test_revenue_priority_b_before_aa(self):
        result = revenue_growth([30,31,32,50,40,30])
        self.assertEqual(result.rule_id, "B-REV-01")

    def test_revenue_aa(self):
        self.assertEqual(revenue_growth([20,25,30,32,35,40]).grade, "AA")

    def test_operating_margin_edges(self):
        self.assertEqual(operating_margin([15,15,15,15]).grade, "AA")
        self.assertEqual(operating_margin([10,10,10,10]).grade, "A")
        self.assertEqual(operating_margin([5,5,5,5]).grade, "B")

    def test_inventory_threshold(self):
        self.assertEqual(inventory_turnover([1.5,1.5,1.5,1.5]).grade, "A")
        self.assertEqual(inventory_turnover([1.6,1.6,1.6,1.6]).grade, "AA")

    def test_fcf_matrix(self):
        self.assertEqual(free_cash_flow([1,1,1,1,1,1]).grade, "AA")
        self.assertEqual(free_cash_flow([-10,-10,4,4,4,4]).grade, "BB")
        self.assertEqual(free_cash_flow([10,10,-4,-4,-4,-4]).grade, "B")
        self.assertEqual(free_cash_flow([-1,-1,-1,-1,-1,-1]).grade, "C")

    def test_na_not_denominator(self):
        results = [
            eps_profitability([2,2,2,2]),
            operating_margin([15,15,15,15]),
            inventory_turnover([], False),
            free_cash_flow([], False),
        ]
        score, count, status = overall(results, 2)
        self.assertEqual(count, 2)
        self.assertEqual(score, Decimal(4))
        self.assertEqual(status, "RANKED")

    def test_net_profit_turnaround(self):
        result = net_profit_growth([10, 12, -2, 3], [0, 0, 0, 0])
        self.assertEqual(result.grade, "BB")
        self.assertEqual(result.rule_id, "BB-NP-02")

    def test_attachment_average_fixture(self):
        values = [3, 3, 1, 4, 2, 0]
        results = [
            GradeResult(str(i), "A", Decimal(value), "FIXTURE", "fixture", {})
            for i, value in enumerate(values)
        ]
        score, count, status = overall(results, 4)
        self.assertEqual(count, 6)
        self.assertEqual(score.quantize(Decimal(".01")), Decimal("2.17"))
        self.assertEqual(status, "RANKED")

    def test_financial_model_na_metrics(self):
        result = RankingEngine().score_financial({
            "revenue_yoy":[10,11,12,13,14,15],
            "operating_margin":[10,11,12,13],
            "net_profit":[1,2,3,4],
            "net_profit_yoy":[1,2,3,4],
            "eps":[1,1,1,1],
        })
        self.assertEqual(result["results"][4].grade, "N/A")
        self.assertEqual(result["results"][5].grade, "N/A")
        self.assertEqual(result["valid_count"], 4)


if __name__ == "__main__":
    unittest.main()
