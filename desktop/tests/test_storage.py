import tempfile
import unittest
from pathlib import Path

from desktop.core.scoring import RankingEngine
from desktop.core.storage import LocalRepository


class StorageTests(unittest.TestCase):
    def test_snapshot_is_persisted_with_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = LocalRepository(Path(directory) / "rank.db")
            result = RankingEngine().score_general({
                "revenue_yoy":[20,25,30,35,40,45],
                "operating_margin":[15,16,17,18],
                "net_profit":[100,110,120,130],
                "net_profit_yoy":[10,12,15,18],
                "eps":[2,2,2,2],
                "inventory_turnover":[2,2,2,2],
                "fcf":[1,1,1,1,1,1],
            })
            item = result | {"symbol":"2330","name":"台積電","market":"上市","industry":"半導體",
                             "aa_count":4,"a_count":2}
            snapshot_id, checksum = repository.publish_snapshot(
                "2026-08-25", "FINAL", "TW6F_GENERAL-v1.2", {"fixture":"2026-08-25"}, [item]
            )
            self.assertEqual(len(checksum), 64)
            self.assertEqual(repository.latest_snapshot()["snapshot_id"], snapshot_id)
            self.assertEqual(len(repository.rankings(snapshot_id)), 1)
            repository.close()

    def test_identical_publish_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = LocalRepository(Path(directory) / "rank.db")
            result = RankingEngine().score_general({
                "revenue_yoy":[20,20,20,20,20,20], "operating_margin":[10,10,10,10],
                "net_profit":[1,2,3,4], "net_profit_yoy":[1,2,3,4], "eps":[1,1,1,1],
                "inventory_turnover":[1,1,1,1], "fcf":[1,1,1,1,1,1],
            })
            item = result | {"symbol":"1001","name":"測試","market":"上市","industry":"測試",
                             "aa_count":1,"a_count":1}
            first, _ = repository.publish_snapshot("2026-08-25","FINAL","v1",{"source":"same"},[item])
            second, _ = repository.publish_snapshot("2026-08-25","FINAL","v1",{"source":"same"},[item])
            self.assertEqual(first, second)
            self.assertEqual(len(repository.snapshots()), 1)
            repository.close()

    def test_dense_rank_does_not_skip_after_tie(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = LocalRepository(Path(directory) / "rank.db")
            engine = RankingEngine()
            base = {
                "revenue_yoy":[20,25,30,35,40,45],
                "operating_margin":[15,16,17,18],
                "net_profit":[100,110,120,130],
                "net_profit_yoy":[10,12,15,18],
                "eps":[2,2,2,2],
                "inventory_turnover":[2,2,2,2],
                "fcf":[1,1,1,1,1,1],
            }
            first = engine.score_general(base)
            weaker = engine.score_general(base | {"eps":[0,0,0,0]})
            items = []
            for symbol, result in [("1001", first), ("1002", first), ("1003", weaker)]:
                items.append(result | {"symbol":symbol,"name":symbol,"market":"上市","industry":"測試",
                                       "aa_count":sum(r.grade=="AA" for r in result["results"]),
                                       "a_count":sum(r.grade=="A" for r in result["results"])})
            snapshot_id, _ = repository.publish_snapshot(
                "2026-08-25", "FINAL", "v1", {"fixture":"tie"}, items
            )
            ranks = [row["rank_model"] for row in repository.rankings(snapshot_id)]
            self.assertEqual(ranks, [1, 1, 2])
            repository.close()

    def test_market_and_industry_ranks_are_grouped(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = LocalRepository(Path(directory) / "rank.db")
            engine = RankingEngine()
            base = {
                "revenue_yoy":[20,25,30,35,40,45], "operating_margin":[15,16,17,18],
                "net_profit":[100,110,120,130], "net_profit_yoy":[10,12,15,18],
                "eps":[2,2,2,2], "inventory_turnover":[2,2,2,2], "fcf":[1,1,1,1,1,1],
            }
            items = []
            for symbol, market, industry, eps in [
                ("1001", "上市", "甲", 2), ("1002", "上市", "乙", 1), ("1003", "上櫃", "甲", 0)
            ]:
                result = engine.score_general(base | {"eps":[eps]*4})
                items.append(result | {"symbol":symbol, "name":symbol, "market":market,
                    "industry":industry, "aa_count":sum(r.grade=="AA" for r in result["results"]),
                    "a_count":sum(r.grade=="A" for r in result["results"])})
            snapshot_id, _ = repository.publish_snapshot("2026-08-25", "FINAL", "v1", {}, items)
            rows = {row["symbol"]: row for row in repository.rankings(snapshot_id)}
            self.assertEqual(rows["1003"]["rank_market"], 1)
            self.assertEqual(rows["1003"]["rank_industry"], 2)
            repository.close()

    def test_security_identifiers_and_symbol_change_keep_history(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = LocalRepository(Path(directory) / "rank.db")
            security_id = repository.upsert_security("1234", "測試公司", "上市", "測試", "TW6F_GENERAL",
                                                     isin="TW0001234000", tax_id="12345678")
            repository.connection.commit()
            repository.record_corporate_action(security_id, "SYMBOL_CHANGE", "2026-01-01", "1234", "5678")
            symbols = repository.connection.execute(
                "SELECT identifier_value,valid_to FROM security_identifiers WHERE security_id=? AND identifier_type='SYMBOL' ORDER BY valid_from",
                (security_id,),
            ).fetchall()
            self.assertEqual([(row[0], row[1]) for row in symbols], [("1234","2026-01-01"),("5678",None)])
            repository.close()


if __name__ == "__main__":
    unittest.main()
