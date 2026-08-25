import json
import tempfile
import unittest
from pathlib import Path

from desktop.core.bronze import merge_tpex_swagger_run, normalize_twse_bronze


class BronzeTests(unittest.TestCase):
    def test_company_and_revenue_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); run = root / "run"; output = root / "silver"; run.mkdir()
            (run / "listed_companies.json").write_text(json.dumps([
                {"公司代號":"2330","公司簡稱":"台積電","產業別":"24","市場別":"上市"},
                {"公司代號":"00ETF","公司簡稱":"非普通股","產業別":""}
            ], ensure_ascii=False), encoding="utf-8")
            (run / "monthly_revenue_listed.json").write_text(json.dumps([
                {"公司代號":"2330","資料年月":"11507","營業收入-去年同月增減(%)":"12.5","出表日期":"2026-08-10"}
            ], ensure_ascii=False), encoding="utf-8")
            report = normalize_twse_bronze(run, output, "2026-08-10")
            self.assertEqual(report["securities"], 1)
            self.assertEqual(report["revenue_facts"], 1)
            self.assertIn("TW6F_GENERAL", (output / "securities.csv").read_text(encoding="utf-8-sig"))
            self.assertEqual(report["status"], "PARTIAL")

    def test_tpex_discovered_data_merges_into_silver(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); run=root/"tpex"; silver=root/"silver"; run.mkdir(); silver.mkdir()
            (silver/"securities.csv").write_text("symbol,name,market,industry,model_code\n2330,台積電,上市,24,TW6F_GENERAL\n",encoding="utf-8")
            (silver/"financial_facts.csv").write_text(
                "symbol,metric_code,period,value,published_at,available_at,scope,unit,version,source_key\n",encoding="utf-8")
            (run/"companies.json").write_text(json.dumps([
                {"公司代號":"6488","公司簡稱":"環球晶","產業別":"24"}
            ],ensure_ascii=False),encoding="utf-8")
            (run/"revenue.json").write_text(json.dumps([
                {"公司代號":"6488","資料年月":"11507","營業收入-去年同月增減(%)":"8.2"}
            ],ensure_ascii=False),encoding="utf-8")
            (run/"manifest.json").write_text(json.dumps({"datasets":[
                {"summary":"上櫃公司基本資料","file":"companies.json"},
                {"summary":"上櫃公司每月營業收入","file":"revenue.json"}
            ]},ensure_ascii=False),encoding="utf-8")
            result=merge_tpex_swagger_run(run,silver,"2026-08-25")
            self.assertEqual(result["securities_total"],2)
            self.assertIn("6488",(silver/"securities.csv").read_text(encoding="utf-8-sig"))
            self.assertEqual(result["tpex_revenue_facts"],1)


if __name__ == "__main__":
    unittest.main()
