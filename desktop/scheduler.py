from __future__ import annotations

import argparse
import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    from .auto_update import run_update
except ImportError:
    from auto_update import run_update


def next_run(hour, minute):
    now = datetime.now()
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return candidate if candidate > now else candidate + timedelta(days=1)


def main():
    parser = argparse.ArgumentParser(description="每日官方資料自動更新排程")
    parser.add_argument("--time", default="19:30", help="本機時間 HH:MM")
    parser.add_argument("--db", default=str(Path.home()/".six_financial_rank"/"rank_local.db"))
    parser.add_argument("--workspace", default=str(Path.home()/".six_financial_rank"/"official_pipeline"))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    hour, minute = map(int, args.time.split(":"))
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("--time 必須為 HH:MM")
    while True:
        if not args.once:
            target = next_run(hour, minute)
            print(f"下一次更新：{target.isoformat(timespec='minutes')}")
            while datetime.now() < target:
                time.sleep(min(30, max(1, (target-datetime.now()).total_seconds())))
        report = run_update(args.db,args.workspace,date.today().isoformat(),"PROVISIONAL")
        print(json.dumps(report,ensure_ascii=False,indent=2))
        if args.once:
            break


if __name__ == "__main__":
    main()
