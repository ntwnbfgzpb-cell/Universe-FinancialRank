from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .scoring import RankingEngine

REQUIRED_SECURITY = {"symbol","name","market","industry","model_code"}
REQUIRED_FACT = {
    "symbol","metric_code","period","value","published_at","available_at",
    "scope","unit","version","source_key"
}
METRIC_MAP = {
    "REVENUE_YOY": "revenue_yoy",
    "OP_MARGIN": "operating_margin",
    "NET_PROFIT": "net_profit",
    "NET_PROFIT_YOY": "net_profit_yoy",
    "EPS": "eps",
    "INVENTORY_TURNOVER_Q": "inventory_turnover",
    "FCF_CORE": "fcf",
}
MODEL_CODES = {"TW6F_GENERAL","TW4F_FINANCIAL","TW4F_SECURITIES"}


class ImportValidationError(ValueError):
    pass


def _read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ImportValidationError(f"{path.name} 沒有表頭")
        yield set(reader.fieldnames), list(reader)


def _check_columns(actual, required, filename):
    missing = required - actual
    if missing:
        raise ImportValidationError(f"{filename} 缺少欄位：{', '.join(sorted(missing))}")


class OfficialImportPipeline:
    def __init__(self, repository):
        self.repository = repository
        self.engine = RankingEngine()
        self.repository.register_rule_set(self.engine.rule_manifest)

    def import_directory(self, directory, as_of_date, snapshot_status="FINAL"):
        directory = Path(directory)
        securities_file = directory / "securities.csv"
        facts_file = directory / "financial_facts.csv"
        if not securities_file.exists() or not facts_file.exists():
            raise ImportValidationError("目錄必須同時包含 securities.csv 與 financial_facts.csv")
        job_id = self.repository.begin_job("OFFICIAL_CSV")
        try:
            sec_columns, securities = next(_read_csv(securities_file))
            fact_columns, facts = next(_read_csv(facts_file))
            _check_columns(sec_columns, REQUIRED_SECURITY, securities_file.name)
            _check_columns(fact_columns, REQUIRED_FACT, facts_file.name)
            security_by_symbol = {}
            for row_no, row in enumerate(securities, start=2):
                if row["model_code"] not in MODEL_CODES:
                    raise ImportValidationError(f"securities.csv 第 {row_no} 列 model_code 無效")
                if row["market"] not in {"上市","上櫃"}:
                    raise ImportValidationError(f"securities.csv 第 {row_no} 列 market 無效")
                security_id = self.repository.upsert_security(
                    row["symbol"].strip(), row["name"].strip(), row["market"].strip(),
                    row["industry"].strip(), row["model_code"].strip(),
                    row.get("isin", "").strip() or None, row.get("tax_id", "").strip() or None,
                    row.get("full_name", "").strip() or None,
                )
                security_by_symbol[row["symbol"].strip()] = (security_id, row)
            self.repository.connection.commit()
            grouped = defaultdict(lambda: defaultdict(list))
            normalized_facts = []
            cutoff = date.fromisoformat(as_of_date)
            for row_no, row in enumerate(facts, start=2):
                symbol = row["symbol"].strip()
                if symbol not in security_by_symbol:
                    raise ImportValidationError(f"financial_facts.csv 第 {row_no} 列代號不存在於證券主檔")
                metric = row["metric_code"].strip()
                if metric not in METRIC_MAP:
                    raise ImportValidationError(f"financial_facts.csv 第 {row_no} 列 metric_code 無效")
                try:
                    value = Decimal(row["value"].strip())
                    published = date.fromisoformat(row["published_at"])
                    available = date.fromisoformat(row["available_at"])
                except (InvalidOperation, ValueError):
                    raise ImportValidationError(f"financial_facts.csv 第 {row_no} 列數值或日期格式錯誤")
                if available > cutoff:
                    continue
                grouped[symbol][metric].append((row["period"].strip(), value))
                normalized_facts.append({
                    "security_id": security_by_symbol[symbol][0], "metric_code": metric,
                    "period": row["period"].strip(), "value": str(value),
                    "published_at": published.isoformat(), "available_at": available.isoformat(),
                    "scope": row["scope"].strip(), "unit": row["unit"].strip(),
                    "version": row["version"].strip(), "source_key": row["source_key"].strip(),
                })
            checksum = hashlib.sha256(facts_file.read_bytes()).hexdigest()
            source_groups = defaultdict(list)
            for fact in normalized_facts:
                source_groups[(fact["source_key"] or facts_file.name, fact["version"])].append(fact)
            for (source_key, version), source_facts in source_groups.items():
                latest_published = max(fact["published_at"] for fact in source_facts)
                group_payload = json.dumps(source_facts, ensure_ascii=False, sort_keys=True).encode()
                group_checksum = hashlib.sha256(group_payload).hexdigest()
                self.repository.store_source_and_facts(
                    "OFFICIAL_CSV", source_key, latest_published, version, group_checksum, source_facts
                )
            # Rebuild from all facts available by the cutoff, so scheduled monthly/quarterly
            # imports accumulate instead of scoring only the latest downloaded file.
            combined = defaultdict(dict)
            for symbol in security_by_symbol:
                for fact in self.repository.financial_facts(symbol, as_of_date):
                    if fact["metric_code"] not in METRIC_MAP:
                        continue
                    combined[symbol][(fact["metric_code"], fact["period"])] = Decimal(fact["value_text"])
            grouped = defaultdict(lambda: defaultdict(list))
            for symbol, facts_by_key in combined.items():
                for (metric, period), value in facts_by_key.items():
                    grouped[symbol][metric].append((period, value))
            scored = []
            for symbol, metrics in grouped.items():
                security_id, security = security_by_symbol[symbol]
                data = {}
                for metric, values in metrics.items():
                    data[METRIC_MAP[metric]] = [v for _, v in sorted(values)]
                model = security["model_code"]
                if model == "TW4F_FINANCIAL":
                    result = self.engine.score_financial(data)
                elif model == "TW4F_SECURITIES":
                    result = self.engine.score_financial(data, securities=True)
                else:
                    result = self.engine.score_general(data)
                result_rows = result["results"]
                scored.append(result | {
                    "symbol": symbol, "name": security["name"], "market": security["market"],
                    "industry": security["industry"],
                    "aa_count": sum(r.grade == "AA" for r in result_rows),
                    "a_count": sum(r.grade == "A" for r in result_rows),
                })
            snapshot_id, snapshot_checksum = self.repository.publish_snapshot(
                as_of_date, snapshot_status, self.engine.rule_version,
                {"provider":"OFFICIAL_CSV","facts_sha256":checksum,
                 "rule_checksum":self.engine.rule_checksum}, scored,
            )
            required_by_model = {
                "TW6F_GENERAL": {"REVENUE_YOY","OP_MARGIN","NET_PROFIT","EPS","INVENTORY_TURNOVER_Q","FCF_CORE"},
                "TW4F_FINANCIAL": {"REVENUE_YOY","OP_MARGIN","NET_PROFIT","EPS"},
                "TW4F_SECURITIES": {"REVENUE_YOY","OP_MARGIN","NET_PROFIT","EPS"},
            }
            for item in scored:
                security_id, security = security_by_symbol[item["symbol"]]
                missing = required_by_model[security["model_code"]] - set(grouped[item["symbol"]])
                if missing:
                    self.repository.add_quality_issue(
                        snapshot_id, security_id, as_of_date, ",".join(sorted(missing)),
                        "CRITICAL" if item["rank_status"] != "RANKED" else "WARNING",
                        "MISSING_REQUIRED_METRIC", f"缺少必要指標：{', '.join(sorted(missing))}", "OFFICIAL_CSV",
                    )
                for result_row in item["results"]:
                    if result_row.grade == "N/A" and "NOT_APPLICABLE" not in result_row.quality_flags:
                        self.repository.add_quality_issue(
                            snapshot_id, security_id, as_of_date, result_row.metric_code, "WARNING",
                            "INSUFFICIENT_METRIC_DATA", result_row.reason_text, "OFFICIAL_CSV",
                        )
            self.repository.finish_job(job_id, "SUCCEEDED", len(normalized_facts))
            return {
                "snapshot_id": snapshot_id, "checksum": snapshot_checksum,
                "securities": len(securities), "facts": len(normalized_facts),
                "ranked": sum(item["rank_status"] == "RANKED" for item in scored),
            }
        except Exception as error:
            self.repository.finish_job(job_id, "FAILED", 0, str(error))
            raise
