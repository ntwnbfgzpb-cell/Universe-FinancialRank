from __future__ import annotations

import csv
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

from .transform import cumulative_to_quarters, core_fcf, inventory_turnover, safe_ratio


class XbrlMappingError(ValueError):
    pass


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def load_mapping(path=None):
    path = Path(path) if path else Path(__file__).parents[1] / "config" / "xbrl_mapping.v1.json"
    mapping = json.loads(path.read_text(encoding="utf-8"))
    if not mapping.get("version") or not isinstance(mapping.get("concepts"), dict):
        raise XbrlMappingError("XBRL mapping 缺少 version 或 concepts")
    reverse = {}
    for target, concepts in mapping["concepts"].items():
        for concept in concepts:
            if concept in reverse:
                raise XbrlMappingError(f"XBRL concept 重複映射：{concept}")
            reverse[concept] = target
    return mapping, reverse


def extract_xbrl(path, mapping_path=None):
    _, reverse = load_mapping(mapping_path)
    root = ET.parse(path).getroot()
    values, unmapped = {}, set()
    known_namespaces = {"xbrli", "link", "xlink"}
    for element in root.iter():
        name = local_name(element.tag)
        if name in reverse and element.text not in (None, ""):
            try:
                value = Decimal(element.text.strip().replace(",", ""))
            except InvalidOperation:
                continue
            target = reverse[name]
            values.setdefault(target, value)
        elif element.text and element.attrib.get("contextRef") and name not in reverse:
            prefix = element.tag.split("}", 1)[0].lstrip("{") if "}" in element.tag else ""
            if not any(token in prefix for token in known_namespaces):
                unmapped.add(name)
    return values, sorted(unmapped)


def normalize_xbrl_directory(directory, output_csv, mapping_path=None):
    """Normalize manifest-described official XBRL filings to scoring fact CSV."""
    directory, output_csv = Path(directory), Path(output_csv)
    manifest_path = directory / "manifest.csv"
    if not manifest_path.exists():
        raise XbrlMappingError("XBRL 目錄必須包含 manifest.csv")
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as file:
        manifest = list(csv.DictReader(file))
    required = {"symbol","fiscal_year","quarter","published_at","available_at","scope","version","file"}
    if not manifest or required - set(manifest[0]):
        raise XbrlMappingError("manifest.csv 欄位不完整")
    filings, unmapped = {}, defaultdict(set)
    for row in manifest:
        quarter = int(row["quarter"])
        if quarter not in {1,2,3,4}:
            raise XbrlMappingError("quarter 必須為 1 至 4")
        values, missing_tags = extract_xbrl(directory / row["file"], mapping_path)
        key = (row["symbol"], int(row["fiscal_year"]), quarter)
        filings[key] = (row, values)
        unmapped[row["symbol"]].update(missing_tags)
    quarterly = {}
    cumulative_fields = ("revenue","operating_income","net_income_parent","basic_eps",
                         "cost_of_goods_sold","cfo","capex_ppe","capex_intangible")
    groups = defaultdict(dict)
    for (symbol, year, quarter), (_, values) in filings.items():
        groups[(symbol, year)][quarter] = values
    for (symbol, year), by_quarter in groups.items():
        converted = {field: cumulative_to_quarters({q:v.get(field) for q,v in by_quarter.items()})
                     for field in cumulative_fields}
        for quarter, raw in by_quarter.items():
            standalone = {field: converted[field][quarter] for field in cumulative_fields}
            standalone["inventory"] = raw.get("inventory")
            quarterly[(symbol, year, quarter)] = standalone
    rows = []
    for key in sorted(quarterly):
        symbol, year, quarter = key
        values = quarterly[key]
        row_meta = filings[key][0]
        prior_key = (symbol, year, quarter-1) if quarter > 1 else (symbol, year-1, 4)
        prior_inventory = quarterly.get(prior_key, {}).get("inventory")
        metrics = {
            "OP_MARGIN": safe_ratio(values.get("operating_income"), values.get("revenue"), 100),
            "NET_PROFIT": values.get("net_income_parent"),
            "EPS": values.get("basic_eps"),
            "INVENTORY_TURNOVER_Q": inventory_turnover(values.get("cost_of_goods_sold"), prior_inventory, values.get("inventory")),
            "FCF_CORE": core_fcf(values.get("cfo"), values.get("capex_ppe"), values.get("capex_intangible")),
        }
        prior_year = quarterly.get((symbol, year-1, quarter), {})
        current_profit, prior_profit = values.get("net_income_parent"), prior_year.get("net_income_parent")
        metrics["NET_PROFIT_YOY"] = None if current_profit is None or prior_profit in (None, Decimal(0)) else (current_profit/prior_profit-1)*100
        for metric, value in metrics.items():
            if value is None:
                continue
            rows.append({"symbol":symbol, "metric_code":metric, "period":f"{year}Q{quarter}",
                "value":str(value), "published_at":row_meta["published_at"],
                "available_at":row_meta["available_at"], "scope":row_meta["scope"],
                "unit":"PERCENT" if metric in {"OP_MARGIN","NET_PROFIT_YOY"} else "RAW",
                "version":row_meta["version"], "source_key":row_meta["file"]})
    fields = ["symbol","metric_code","period","value","published_at","available_at",
              "scope","unit","version","source_key"]
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    report = {"filings":len(filings), "facts":len(rows),
              "unmapped_concepts":{symbol:sorted(items) for symbol,items in unmapped.items() if items}}
    output_csv.with_suffix(".report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
