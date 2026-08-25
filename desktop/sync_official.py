from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .core.providers import TwseOpenApiRawAdapter
except ImportError:
    from core.providers import TwseOpenApiRawAdapter


def main():
    parser = argparse.ArgumentParser(description="同步證交所 OpenAPI 原始資料到 Bronze 快取")
    parser.add_argument("--output", default=str(Path.home() / ".six_financial_rank" / "official_raw"))
    parser.add_argument("--dataset", action="append", dest="datasets")
    args = parser.parse_args()
    run_dir, manifest = TwseOpenApiRawAdapter(args.output).sync(args.datasets)
    print(f"完成：{run_dir}")
    for item in manifest["datasets"]:
        print(f"{item['name']}: {item['rows']} rows {item['sha256'][:12]}…")


if __name__ == "__main__":
    main()
