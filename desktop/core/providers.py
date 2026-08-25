from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.request import Request, urlopen


class ProviderAdapter(ABC):
    provider_code: str

    @abstractmethod
    def securities(self):
        raise NotImplementedError

    @abstractmethod
    def financial_facts(self):
        raise NotImplementedError


class OfficialCsvAdapter(ProviderAdapter):
    """離線匯入官方下載 CSV；不以示範資料冒充線上官方結果。"""

    provider_code = "OFFICIAL_CSV"

    def __init__(self, securities_file: str | Path, facts_file: str | Path):
        self.securities_file = Path(securities_file)
        self.facts_file = Path(facts_file)

    @staticmethod
    def _read(path):
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            yield from csv.DictReader(file)

    def securities(self):
        return list(self._read(self.securities_file))

    def financial_facts(self):
        return list(self._read(self.facts_file))


class TwseOpenApiRawAdapter:
    """Download verified TWSE OpenAPI datasets into an immutable Bronze cache."""

    provider_code = "TWSE_OPENAPI"
    BASE = "https://openapi.twse.com.tw/v1"
    DATASETS = {
        "listed_companies": "/opendata/t187ap03_L",
        "public_companies": "/opendata/t187ap03_P",
        "monthly_revenue_listed": "/opendata/t187ap05_L",
        "monthly_revenue_public": "/opendata/t187ap05_P",
        "income_general": "/opendata/t187ap06_X_ci",
        "income_financial": "/opendata/t187ap06_X_basi",
        "income_securities": "/opendata/t187ap06_X_bd",
        "income_holding": "/opendata/t187ap06_X_fh",
        "income_insurance": "/opendata/t187ap06_X_ins",
        "balance_general": "/opendata/t187ap07_X_ci",
        "balance_financial": "/opendata/t187ap07_X_basi",
        "balance_securities": "/opendata/t187ap07_X_bd",
        "balance_holding": "/opendata/t187ap07_X_fh",
        "balance_insurance": "/opendata/t187ap07_X_ins"
    }

    def __init__(self, cache_directory: str | Path, timeout=30):
        self.cache_directory = Path(cache_directory)
        self.timeout = timeout

    def sync(self, selected=None):
        selected = selected or self.DATASETS.keys()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = self.cache_directory / timestamp
        run_dir.mkdir(parents=True, exist_ok=False)
        manifest = {"provider": self.provider_code, "fetched_at": timestamp, "datasets": []}
        try:
            for name in selected:
                if name not in self.DATASETS:
                    raise ValueError(f"未知或未允許的官方資料集：{name}")
                url = self.BASE + self.DATASETS[name]
                request = Request(url, headers={"Accept":"application/json", "User-Agent":"TW-Rank-Research/0.5"})
                with urlopen(request, timeout=self.timeout) as response:
                    payload = response.read()
                    content_type = response.headers.get("Content-Type", "")
                decoded = json.loads(payload.decode("utf-8-sig"))
                if not isinstance(decoded, list):
                    raise ValueError(f"{name} 回傳格式不是 JSON 陣列")
                path = run_dir / f"{name}.json"
                path.write_bytes(payload)
                manifest["datasets"].append({"name": name, "url": url, "rows": len(decoded),
                    "sha256": hashlib.sha256(payload).hexdigest(), "content_type": content_type,
                    "file": path.name})
            (run_dir / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            (run_dir / "FAILED").write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
            raise
        return run_dir, manifest
