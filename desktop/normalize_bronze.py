from __future__ import annotations

import argparse
import json

try:
    from .core.bronze import normalize_twse_bronze
except ImportError:
    from core.bronze import normalize_twse_bronze


def main():
    parser = argparse.ArgumentParser(description="將證交所 Bronze 原始資料轉為保守的 Silver 匯入包")
    parser.add_argument("run_directory")
    parser.add_argument("output_directory")
    parser.add_argument("--available-at")
    args = parser.parse_args()
    print(json.dumps(normalize_twse_bronze(
        args.run_directory, args.output_directory, args.available_at
    ), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
