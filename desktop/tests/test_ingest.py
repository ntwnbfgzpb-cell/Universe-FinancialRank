import csv
import tempfile
import unittest
from pathlib import Path

from desktop.core.ingest import ImportValidationError, OfficialImportPipeline
from desktop.core.storage import LocalRepository


class IngestTests(unittest.TestCase):
    def _dataset(self, directory):
        directory = Path(directory)
        with (directory / "securities.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["symbol","name","market","industry","model_code"])
            writer.writeheader()
            writer.writerow({"symbol":"2330","name":"台積電","market":"上市","industry":"半導體","model_code":"TW6F_GENERAL"})
        rows = []
        def add(metric, values):
            for index, value in enumerate(values, start=1):
                rows.append({
                    "symbol":"2330","metric_code":metric,"period":f"2025-{index:02d}",
                    "value":value,"published_at":"2026-01-10","available_at":"2026-01-10",
                    "scope":"CONSOLIDATED","unit":"PERCENT","version":"v1","source_key":"fixture",
                })
        add("REVENUE_YOY",[20,22,24,26,28,30])
        add("OP_MARGIN",[15,16,17,18])
        add("NET_PROFIT",[100,110,120,130])
        add("NET_PROFIT_YOY",[10,11,12,13])
        add("EPS",[2,2,2,2])
        add("INVENTORY_TURNOVER_Q",[2,2,2,2])
        add("FCF_CORE",[1,1,1,1,1,1])
        with (directory / "financial_facts.csv").open("w", encoding="utf-8", newline="") as file:
            fields=["symbol","metric_code","period","value","published_at","available_at","scope","unit","version","source_key"]
            writer=csv.DictWriter(file,fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_complete_import_publishes_ranked_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            self._dataset(directory)
            repository=LocalRepository(Path(directory)/"rank.db")
            result=OfficialImportPipeline(repository).import_directory(directory,"2026-08-25")
            self.assertEqual(result["securities"],1)
            self.assertEqual(result["ranked"],1)
            snapshot=repository.latest_snapshot()
            self.assertEqual(snapshot["status"],"FINAL")
            self.assertEqual(len(repository.rankings(snapshot["snapshot_id"])),1)
            self.assertEqual(repository.quality_summary()["ranked"], 1)
            repository.close()

    def test_missing_files_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            repository=LocalRepository(Path(directory)/"rank.db")
            with self.assertRaises(ImportValidationError):
                OfficialImportPipeline(repository).import_directory(directory,"2026-08-25")
            repository.close()


if __name__ == "__main__":
    unittest.main()
