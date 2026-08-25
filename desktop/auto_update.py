from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

try:
    from .core.bronze import merge_tpex_swagger_run, normalize_twse_bronze
    from .core.downloads import MopsPublicFileAdapter, OfficialDownloadError, SwaggerOfficialAdapter
    from .core.ingest import OfficialImportPipeline
    from .core.providers import TwseOpenApiRawAdapter
    from .core.storage import LocalRepository
    from .core.xbrl import normalize_xbrl_directory
except ImportError:
    from core.bronze import merge_tpex_swagger_run, normalize_twse_bronze
    from core.downloads import MopsPublicFileAdapter, OfficialDownloadError, SwaggerOfficialAdapter
    from core.ingest import OfficialImportPipeline
    from core.providers import TwseOpenApiRawAdapter
    from core.storage import LocalRepository
    from core.xbrl import normalize_xbrl_directory


FACT_FIELDS = ["symbol","metric_code","period","value","published_at","available_at",
               "scope","unit","version","source_key"]


def append_facts(target, source):
    with Path(target).open("a", encoding="utf-8-sig", newline="") as output, \
         Path(source).open("r", encoding="utf-8-sig", newline="") as input_file:
        writer = csv.DictWriter(output, fieldnames=FACT_FIELDS)
        for row in csv.DictReader(input_file):
            writer.writerow({field:row.get(field, "") for field in FACT_FIELDS})


def run_update(database, workspace, as_of_date, status="PROVISIONAL", xbrl_directory=None,
               include_tpex=True, mops_index=None):
    workspace = Path(workspace); workspace.mkdir(parents=True, exist_ok=True)
    report = {"as_of_date":as_of_date,"status":status,"steps":[],"warnings":[]}
    twse_dir, twse_manifest = TwseOpenApiRawAdapter(workspace / "bronze" / "twse").sync()
    report["steps"].append({"step":"TWSE_BRONZE","datasets":len(twse_manifest["datasets"]),"path":str(twse_dir)})
    silver = workspace / "silver" / twse_dir.name
    normalization = normalize_twse_bronze(twse_dir, silver, as_of_date)
    report["steps"].append({"step":"TWSE_SILVER","result":normalization,"path":str(silver)})
    if include_tpex:
        try:
            tpex_dir, manifest = SwaggerOfficialAdapter(
                "https://www.tpex.org.tw/openapi/swagger.json", workspace / "bronze" / "tpex",
                ("上櫃公司基本資料","上櫃公司每月營業收入","上櫃股票"), max_endpoints=10,
            ).sync()
            report["steps"].append({"step":"TPEX_BRONZE","datasets":len(manifest["datasets"]),"path":str(tpex_dir)})
            tpex_silver = merge_tpex_swagger_run(tpex_dir, silver, as_of_date)
            report["steps"].append({"step":"TPEX_SILVER","result":tpex_silver})
        except OfficialDownloadError as error:
            report["warnings"].append(f"TPEx：{error}")
    if mops_index:
        try:
            mops_dir, manifest = MopsPublicFileAdapter(mops_index, workspace / "bronze" / "mops").sync()
            report["steps"].append({"step":"MOPS_PUBLIC_FILES","files":len(manifest["files"]),"path":str(mops_dir)})
        except OfficialDownloadError as error:
            report["warnings"].append(f"MOPS：{error}")
    if xbrl_directory:
        xbrl_facts = silver / "xbrl_financial_facts.csv"
        xbrl_report = normalize_xbrl_directory(xbrl_directory, xbrl_facts)
        append_facts(silver / "financial_facts.csv", xbrl_facts)
        report["steps"].append({"step":"XBRL_SILVER","result":xbrl_report})
    repository = LocalRepository(database)
    try:
        result = OfficialImportPipeline(repository).import_directory(silver, as_of_date, status)
    finally:
        repository.close()
    report["steps"].append({"step":"GOLD_SNAPSHOT","result":result})
    report_path = workspace / f"auto_update_{as_of_date}.json"
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="官方資料自動取得、正規化、評分與快照")
    parser.add_argument("--db", default=str(Path.home()/".six_financial_rank"/"rank_local.db"))
    parser.add_argument("--workspace", default=str(Path.home()/".six_financial_rank"/"official_pipeline"))
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--status", choices=["PROVISIONAL","FINAL"], default="PROVISIONAL")
    parser.add_argument("--xbrl-directory")
    parser.add_argument("--mops-index")
    parser.add_argument("--skip-tpex", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run_update(args.db,args.workspace,args.as_of,args.status,args.xbrl_directory,
                                not args.skip_tpex,args.mops_index),ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
