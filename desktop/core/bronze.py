from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path


def pick(row, *names, default=""):
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value).strip()
    return default


def model_for(industry_code, company_name):
    if "證券" in company_name or "期貨" in company_name:
        return "TW4F_SECURITIES"
    if industry_code == "17":
        return "TW4F_FINANCIAL"
    return "TW6F_GENERAL"


def normalize_twse_bronze(run_directory, output_directory, available_at=None):
    """Create a conservative partial Silver import package from TWSE Bronze JSON."""
    run, output = Path(run_directory), Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    available_at = available_at or date.today().isoformat()
    company_files = [run / "public_companies.json", run / "listed_companies.json"]
    company_file = next((path for path in company_files if path.exists()), None)
    revenue_files = [run / "monthly_revenue_public.json", run / "monthly_revenue_listed.json"]
    revenue_file = next((path for path in revenue_files if path.exists()), None)
    if not company_file or not revenue_file:
        raise ValueError("Bronze 目錄缺少公司主檔或月營收資料")
    companies = json.loads(company_file.read_text(encoding="utf-8-sig"))
    revenues = json.loads(revenue_file.read_text(encoding="utf-8-sig"))
    securities = {}
    for row in companies:
        symbol = pick(row, "公司代號", "公司代码", "Code")
        if not symbol or not symbol.isdigit() or len(symbol) != 4:
            continue
        name = pick(row, "公司簡稱", "公司名稱", "CompanyName")
        industry = pick(row, "產業別", "產業類別", "Industry", default="未分類")
        market_raw = pick(row, "市場別", "市場", "Market")
        market = "上櫃" if "上櫃" in market_raw else "上市"
        securities[symbol] = {"symbol":symbol, "name":name, "market":market,
            "industry":industry, "model_code":model_for(industry, name)}
    facts = []
    for row in revenues:
        symbol = pick(row, "公司代號", "公司代码", "Code")
        if symbol not in securities:
            continue
        yoy = pick(row, "營業收入-去年同月增減(%)", "去年同月增減(%)", "YoY")
        period = pick(row, "資料年月", "年月", "YearMonth")
        if not yoy or not period:
            continue
        published = pick(row, "出表日期", "公告日期", "Date", default=available_at)
        if len(published) != 10 or "-" not in published:
            published = available_at
        facts.append({"symbol":symbol, "metric_code":"REVENUE_YOY", "period":period,
            "value":yoy.replace(",", ""), "published_at":published, "available_at":available_at,
            "scope":"CONSOLIDATED", "unit":"PERCENT", "version":"TWSE_OPENAPI",
            "source_key":f"{revenue_file.name}:{period}"})
    with (output / "securities.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["symbol","name","market","industry","model_code"])
        writer.writeheader(); writer.writerows(securities.values())
    fields = ["symbol","metric_code","period","value","published_at","available_at",
              "scope","unit","version","source_key"]
    with (output / "financial_facts.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader(); writer.writerows(facts)
    report = {"status":"PARTIAL", "securities":len(securities), "revenue_facts":len(facts),
              "missing":"quarterly taxonomy mappings required before FINAL rank"}
    (output / "NORMALIZATION_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def merge_tpex_swagger_run(run_directory, silver_directory, available_at=None):
    """Merge discovered TPEx company/revenue datasets into an existing Silver package."""
    run, silver = Path(run_directory), Path(silver_directory)
    available_at = available_at or date.today().isoformat()
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    companies, revenues = [], []
    for dataset in manifest.get("datasets", []):
        summary = dataset.get("summary", "")
        try:
            rows = json.loads((run / dataset["file"]).read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if "基本資料" in summary:
            companies.extend(rows if isinstance(rows, list) else [])
        elif "營業收入" in summary or "月營收" in summary:
            revenues.extend(rows if isinstance(rows, list) else [])
    existing = {}
    securities_path = silver / "securities.csv"
    with securities_path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file): existing[row["symbol"]] = row
    for row in companies:
        symbol = pick(row, "公司代號", "證券代號", "SecuritiesCompanyCode", "Code")
        if not symbol.isdigit() or len(symbol) != 4:
            continue
        name = pick(row, "公司簡稱", "公司名稱", "證券名稱", "CompanyName")
        industry = pick(row, "產業別", "產業類別", "Industry", default="未分類")
        existing[symbol] = {"symbol":symbol,"name":name,"market":"上櫃","industry":industry,
                            "model_code":model_for(industry,name)}
    with securities_path.open("w",encoding="utf-8-sig",newline="") as file:
        writer=csv.DictWriter(file,fieldnames=["symbol","name","market","industry","model_code"])
        writer.writeheader(); writer.writerows(existing.values())
    facts_path = silver / "financial_facts.csv"
    fact_rows = []
    for row in revenues:
        symbol = pick(row,"公司代號","證券代號","Code")
        if symbol not in existing: continue
        yoy = pick(row,"營業收入-去年同月增減(%)","去年同月增減(%)","YoY")
        period = pick(row,"資料年月","年月","YearMonth")
        if yoy and period:
            fact_rows.append({"symbol":symbol,"metric_code":"REVENUE_YOY","period":period,
                "value":yoy.replace(",",""),"published_at":available_at,"available_at":available_at,
                "scope":"CONSOLIDATED","unit":"PERCENT","version":"TPEX_OPENAPI",
                "source_key":f"TPEX_SWAGGER_DISCOVERY:{period}"})
    fields=["symbol","metric_code","period","value","published_at","available_at","scope","unit","version","source_key"]
    with facts_path.open("a",encoding="utf-8-sig",newline="") as file:
        writer=csv.DictWriter(file,fieldnames=fields); writer.writerows(fact_rows)
    return {"securities_total":len(existing),"tpex_revenue_facts":len(fact_rows)}
