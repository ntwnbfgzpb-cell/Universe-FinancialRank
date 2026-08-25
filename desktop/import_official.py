from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .core import LocalRepository
    from .core.ingest import OfficialImportPipeline
except ImportError:
    from core import LocalRepository
    from core.ingest import OfficialImportPipeline


def main():
    parser = argparse.ArgumentParser(description="匯入官方下載 CSV 並建立不可變 Rank 快照")
    parser.add_argument("directory", help="包含 securities.csv 與 financial_facts.csv 的目錄")
    parser.add_argument("--as-of", required=True, help="快照日期 YYYY-MM-DD")
    parser.add_argument("--status", choices=["FINAL","PROVISIONAL"], default="FINAL")
    parser.add_argument("--db", default=str(Path(__file__).parent / "data" / "rank_local.db"))
    args = parser.parse_args()
    repository = LocalRepository(args.db)
    try:
        result = OfficialImportPipeline(repository).import_directory(args.directory, args.as_of, args.status)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        repository.close()


if __name__ == "__main__":
    main()
