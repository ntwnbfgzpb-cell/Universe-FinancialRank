import csv
import tempfile
import unittest
from pathlib import Path

from desktop.core.xbrl import XbrlMappingError, normalize_xbrl_directory


def xbrl(values):
    body = "".join(f'<ifrs:{name} contextRef="c">{value}</ifrs:{name}>' for name,value in values.items())
    return f'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:ifrs="http://xbrl.ifrs.org/taxonomy/2024">{body}</xbrli:xbrl>'


class XbrlTests(unittest.TestCase):
    def test_exact_mapping_quarterization_and_fcf(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fields = ["symbol","fiscal_year","quarter","published_at","available_at","scope","version","file"]
            manifest = []
            for quarter, cumulative in enumerate((10,25,45,70), start=1):
                filename = f"2330_2025Q{quarter}.xbrl"
                (root / filename).write_text(xbrl({
                    "Revenue": cumulative*10, "OperatingIncomeLoss": cumulative*2,
                    "ProfitLossAttributableToOwnersOfParent": cumulative,
                    "BasicEarningsLossPerShare": quarter, "Inventories": 100+quarter*10,
                    "CostOfGoodsSold": cumulative*5,
                    "NetCashFlowsFromUsedInOperatingActivities": cumulative*4,
                    "AcquisitionOfPropertyPlantAndEquipment": -cumulative,
                    "AcquisitionOfIntangibleAssets": cumulative/10,
                }), encoding="utf-8")
                manifest.append({"symbol":"2330","fiscal_year":"2025","quarter":quarter,
                    "published_at":"2026-01-01","available_at":"2026-01-01",
                    "scope":"CONSOLIDATED","version":"v1","file":filename})
            with (root / "manifest.csv").open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fields); writer.writeheader(); writer.writerows(manifest)
            output = root / "facts.csv"
            report = normalize_xbrl_directory(root, output)
            self.assertEqual(report["filings"], 4)
            with output.open(encoding="utf-8-sig") as file:
                rows = list(csv.DictReader(file))
            q4_profit = next(row for row in rows if row["period"] == "2025Q4" and row["metric_code"] == "NET_PROFIT")
            self.assertEqual(q4_profit["value"], "25")
            self.assertTrue(any(row["metric_code"] == "FCF_CORE" for row in rows))

    def test_manifest_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(XbrlMappingError):
                normalize_xbrl_directory(directory, Path(directory) / "facts.csv")


if __name__ == "__main__":
    unittest.main()
