from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS companies(
 company_id TEXT PRIMARY KEY, name TEXT NOT NULL, full_name TEXT, tax_id TEXT,
 country TEXT NOT NULL DEFAULT 'TW', status TEXT NOT NULL DEFAULT 'ACTIVE'
);
CREATE TABLE IF NOT EXISTS securities(
 security_id TEXT PRIMARY KEY, symbol TEXT NOT NULL, name TEXT NOT NULL,
 market TEXT NOT NULL, industry TEXT NOT NULL, model_code TEXT NOT NULL,
 valid_from TEXT NOT NULL, valid_to TEXT
);
CREATE TABLE IF NOT EXISTS security_identifiers(
 security_id TEXT NOT NULL, identifier_type TEXT NOT NULL, identifier_value TEXT NOT NULL,
 valid_from TEXT NOT NULL, valid_to TEXT,
 PRIMARY KEY(security_id,identifier_type,identifier_value,valid_from),
 FOREIGN KEY(security_id) REFERENCES securities(security_id)
);
CREATE TABLE IF NOT EXISTS security_companies(
 security_id TEXT NOT NULL, company_id TEXT NOT NULL, valid_from TEXT NOT NULL, valid_to TEXT,
 PRIMARY KEY(security_id,company_id,valid_from),
 FOREIGN KEY(security_id) REFERENCES securities(security_id),
 FOREIGN KEY(company_id) REFERENCES companies(company_id)
);
CREATE TABLE IF NOT EXISTS industry_mappings(
 security_id TEXT NOT NULL, official_industry TEXT NOT NULL, model_code TEXT NOT NULL,
 peer_group TEXT NOT NULL, effective_from TEXT NOT NULL, effective_to TEXT,
 PRIMARY KEY(security_id,effective_from), FOREIGN KEY(security_id) REFERENCES securities(security_id)
);
CREATE TABLE IF NOT EXISTS ranking_snapshots(
 snapshot_id TEXT PRIMARY KEY, as_of_date TEXT NOT NULL, status TEXT NOT NULL,
 rule_version TEXT NOT NULL, source_cutoffs_json TEXT NOT NULL, checksum TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS metric_results(
 snapshot_id TEXT NOT NULL, security_id TEXT NOT NULL, metric_code TEXT NOT NULL,
 grade TEXT NOT NULL, score TEXT, rule_id TEXT NOT NULL, reason_text TEXT NOT NULL,
 inputs_json TEXT NOT NULL, quality_flags_json TEXT NOT NULL, decision_trace_json TEXT NOT NULL,
 PRIMARY KEY(snapshot_id, security_id, metric_code),
 FOREIGN KEY(snapshot_id) REFERENCES ranking_snapshots(snapshot_id),
 FOREIGN KEY(security_id) REFERENCES securities(security_id)
);
CREATE TABLE IF NOT EXISTS stock_rankings(
 snapshot_id TEXT NOT NULL, security_id TEXT NOT NULL, model_code TEXT NOT NULL,
 overall_score TEXT, valid_count INTEGER NOT NULL, rank_status TEXT NOT NULL,
 rank_model INTEGER, rank_market INTEGER, rank_industry INTEGER, model_percentile TEXT,
 PRIMARY KEY(snapshot_id, security_id),
 FOREIGN KEY(snapshot_id) REFERENCES ranking_snapshots(snapshot_id),
 FOREIGN KEY(security_id) REFERENCES securities(security_id)
);
CREATE TABLE IF NOT EXISTS source_documents(
 source_id TEXT PRIMARY KEY, provider TEXT NOT NULL, source_key TEXT NOT NULL,
 published_at TEXT NOT NULL, fetched_at TEXT NOT NULL, sha256 TEXT NOT NULL,
 version TEXT NOT NULL, UNIQUE(provider, source_key, version)
);
CREATE TABLE IF NOT EXISTS financial_facts(
 fact_id INTEGER PRIMARY KEY AUTOINCREMENT, security_id TEXT NOT NULL,
 metric_code TEXT NOT NULL, period TEXT NOT NULL, value_text TEXT NOT NULL,
 published_at TEXT NOT NULL, available_at TEXT NOT NULL, statement_scope TEXT NOT NULL,
 unit TEXT NOT NULL, version TEXT NOT NULL, source_id TEXT NOT NULL,
 UNIQUE(security_id, metric_code, period, statement_scope, version),
 FOREIGN KEY(security_id) REFERENCES securities(security_id),
 FOREIGN KEY(source_id) REFERENCES source_documents(source_id)
);
CREATE TABLE IF NOT EXISTS ingestion_jobs(
 job_id TEXT PRIMARY KEY, provider TEXT NOT NULL, started_at TEXT NOT NULL,
 ended_at TEXT, status TEXT NOT NULL, row_count INTEGER NOT NULL DEFAULT 0,
 error_text TEXT, retry_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS data_quality_issues(
 issue_id INTEGER PRIMARY KEY AUTOINCREMENT, snapshot_id TEXT, security_id TEXT,
 period TEXT, field TEXT NOT NULL, severity TEXT NOT NULL, code TEXT NOT NULL,
 details TEXT NOT NULL, provider TEXT NOT NULL, created_at TEXT NOT NULL,
 resolved_at TEXT,
 FOREIGN KEY(snapshot_id) REFERENCES ranking_snapshots(snapshot_id),
 FOREIGN KEY(security_id) REFERENCES securities(security_id)
);
CREATE TABLE IF NOT EXISTS ranking_populations(
 snapshot_id TEXT NOT NULL, population_type TEXT NOT NULL, population_key TEXT NOT NULL,
 eligible_count INTEGER NOT NULL, excluded_count INTEGER NOT NULL,
 PRIMARY KEY(snapshot_id,population_type,population_key),
 FOREIGN KEY(snapshot_id) REFERENCES ranking_snapshots(snapshot_id)
);
CREATE TABLE IF NOT EXISTS corporate_actions(
 action_id INTEGER PRIMARY KEY AUTOINCREMENT, security_id TEXT NOT NULL,
 event_type TEXT NOT NULL, effective_date TEXT NOT NULL, old_value TEXT, new_value TEXT,
 ratio TEXT, source_id TEXT, created_at TEXT NOT NULL,
 FOREIGN KEY(security_id) REFERENCES securities(security_id)
);
CREATE TABLE IF NOT EXISTS metric_rule_sets(
 version TEXT PRIMARY KEY, effective_at TEXT NOT NULL, config_json TEXT NOT NULL,
 checksum TEXT NOT NULL, created_at TEXT NOT NULL
);
"""


class LocalRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)

    def close(self):
        self.connection.close()

    def upsert_security(self, symbol, name, market, industry, model_code,
                        isin=None, tax_id=None, full_name=None):
        security_id = f"TW-{market}-{symbol}"
        company_key = tax_id or isin or security_id
        company_id = hashlib.sha256(f"COMPANY|{company_key}".encode()).hexdigest()[:24]
        self.connection.execute(
            """INSERT INTO companies(company_id,name,full_name,tax_id) VALUES(?,?,?,?)
               ON CONFLICT(company_id) DO UPDATE SET name=excluded.name,
               full_name=COALESCE(excluded.full_name,companies.full_name),
               tax_id=COALESCE(excluded.tax_id,companies.tax_id)""",
            (company_id, name, full_name, tax_id),
        )
        self.connection.execute(
            """INSERT INTO securities(security_id,symbol,name,market,industry,model_code,valid_from)
               VALUES(?,?,?,?,?,?,?) ON CONFLICT(security_id) DO UPDATE SET
               name=excluded.name, market=excluded.market, industry=excluded.industry,
               model_code=excluded.model_code""",
            (security_id, symbol, name, market, industry, model_code, "1900-01-01"),
        )
        self.connection.execute(
            "INSERT OR IGNORE INTO security_companies VALUES(?,?,?,?)",
            (security_id, company_id, "1900-01-01", None),
        )
        for identifier_type, value in (("SYMBOL", symbol), ("ISIN", isin), ("TAX_ID", tax_id)):
            if value:
                self.connection.execute(
                    "INSERT OR IGNORE INTO security_identifiers VALUES(?,?,?,?,?)",
                    (security_id, identifier_type, value, "1900-01-01", None),
                )
        self.connection.execute(
            """INSERT OR IGNORE INTO industry_mappings
               (security_id,official_industry,model_code,peer_group,effective_from)
               VALUES(?,?,?,?,?)""", (security_id, industry, model_code, industry, "1900-01-01")
        )
        return security_id

    def register_rule_set(self, manifest):
        config = {key:value for key,value in manifest.items() if key != "checksum"}
        self.connection.execute(
            """INSERT OR IGNORE INTO metric_rule_sets VALUES(?,?,?,?,?)""",
            (manifest["version"], manifest["effective_from"],
             json.dumps(config, ensure_ascii=False, sort_keys=True), manifest["checksum"],
             datetime.now(timezone.utc).isoformat()),
        )
        self.connection.commit()

    def record_corporate_action(self, security_id, event_type, effective_date,
                                old_value=None, new_value=None, ratio=None, source_id=None):
        with self.connection:
            self.connection.execute(
                """INSERT INTO corporate_actions
                   (security_id,event_type,effective_date,old_value,new_value,ratio,source_id,created_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (security_id,event_type,effective_date,old_value,new_value,ratio,source_id,
                 datetime.now(timezone.utc).isoformat()),
            )
            if event_type == "SYMBOL_CHANGE" and old_value and new_value:
                self.connection.execute(
                    "UPDATE security_identifiers SET valid_to=? WHERE security_id=? AND identifier_type='SYMBOL' AND identifier_value=? AND valid_to IS NULL",
                    (effective_date, security_id, old_value),
                )
                self.connection.execute(
                    "INSERT INTO security_identifiers VALUES(?,?,?,?,?)",
                    (security_id, "SYMBOL", new_value, effective_date, None),
                )

    def publish_snapshot(self, as_of_date, status, rule_version, source_cutoffs, scored):
        payload = json.dumps(scored, ensure_ascii=False, sort_keys=True, default=str)
        checksum = hashlib.sha256(payload.encode()).hexdigest()
        cutoffs_json = json.dumps(source_cutoffs, ensure_ascii=False, sort_keys=True)
        existing = self.connection.execute(
            """SELECT snapshot_id FROM ranking_snapshots
               WHERE as_of_date=? AND status=? AND rule_version=?
               AND source_cutoffs_json=? AND checksum=? ORDER BY created_at LIMIT 1""",
            (as_of_date, status, rule_version, cutoffs_json, checksum),
        ).fetchone()
        if existing:
            return existing["snapshot_id"], checksum
        snapshot_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute(
                "INSERT INTO ranking_snapshots VALUES(?,?,?,?,?,?,?)",
                (snapshot_id, as_of_date, status, rule_version, cutoffs_json, checksum, created_at),
            )
            rankable = [item for item in scored if item["overall_score"] is not None]
            sort_key = lambda item: (-float(item["overall_score"]), -item.get("aa_count", 0),
                                     -item.get("a_count", 0), -item["valid_count"], item["symbol"])
            tie_key = lambda item: (item["overall_score"], item.get("aa_count", 0),
                                    item.get("a_count", 0), item["valid_count"])

            def grouped_ranks(group_key):
                result = {}
                groups = {}
                for candidate in rankable:
                    groups.setdefault(group_key(candidate), []).append(candidate)
                for members in groups.values():
                    previous, dense_rank, tie_percentile = None, 0, None
                    for position, candidate in enumerate(sorted(members, key=sort_key), start=1):
                        key = tie_key(candidate)
                        if key != previous:
                            dense_rank += 1
                            tie_percentile = (len(members) - position + 1) * 100 / len(members)
                        previous = key
                        result[candidate["symbol"]] = (dense_rank, tie_percentile)
                return result

            model_ranks = grouped_ranks(lambda item: item["model_code"])
            market_ranks = grouped_ranks(lambda item: (item["model_code"], item["market"]))
            industry_ranks = grouped_ranks(lambda item: (item["model_code"], item["industry"]))
            for item in sorted(rankable, key=sort_key):
                security_id = self.upsert_security(item["symbol"], item["name"], item["market"],
                                                   item["industry"], item["model_code"])
                rank_model, percentile = model_ranks[item["symbol"]]
                rank_market, _ = market_ranks[item["symbol"]]
                rank_industry, _ = industry_ranks[item["symbol"]]
                self.connection.execute(
                    """INSERT INTO stock_rankings VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (snapshot_id, security_id, item["model_code"], str(item["overall_score"]),
                     item["valid_count"], item["rank_status"], rank_model, rank_market,
                     rank_industry, str(percentile)),
                )
                for result in item["results"]:
                    self.connection.execute(
                        """INSERT INTO metric_results VALUES(?,?,?,?,?,?,?,?,?,?)""",
                        (snapshot_id, security_id, result.metric_code, result.grade,
                         None if result.score is None else str(result.score), result.rule_id,
                         result.reason_text, json.dumps(result.inputs, ensure_ascii=False),
                         json.dumps(result.quality_flags, ensure_ascii=False),
                        json.dumps([step.__dict__ for step in result.decision_trace], ensure_ascii=False)),
                    )
            population_specs = {
                "MODEL": lambda item: item["model_code"],
                "MARKET": lambda item: f'{item["model_code"]}|{item["market"]}',
                "INDUSTRY": lambda item: f'{item["model_code"]}|{item["industry"]}',
            }
            for population_type, key_fn in population_specs.items():
                keys = {key_fn(item) for item in scored}
                for population_key in keys:
                    members = [item for item in scored if key_fn(item) == population_key]
                    eligible = sum(item["overall_score"] is not None for item in members)
                    self.connection.execute(
                        "INSERT INTO ranking_populations VALUES(?,?,?,?,?)",
                        (snapshot_id, population_type, population_key, eligible, len(members)-eligible),
                    )
        return snapshot_id, checksum

    def latest_snapshot(self, status="FINAL"):
        if status is None:
            return self.connection.execute(
                "SELECT * FROM ranking_snapshots ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return self.connection.execute(
            "SELECT * FROM ranking_snapshots WHERE status=? ORDER BY created_at DESC LIMIT 1", (status,)
        ).fetchone()

    def rankings(self, snapshot_id):
        return self.connection.execute(
            """SELECT r.*,s.symbol,s.name,s.market,s.industry
               FROM stock_rankings r JOIN securities s USING(security_id)
               WHERE snapshot_id=? ORDER BY rank_model,s.symbol""", (snapshot_id,)
        ).fetchall()

    def latest_facts_by_security(self):
        rows = self.connection.execute(
            """SELECT security_id,metric_code,value_text,unit,period FROM (
                 SELECT security_id,metric_code,value_text,unit,period,
                        ROW_NUMBER() OVER(PARTITION BY security_id,metric_code
                                          ORDER BY period DESC,available_at DESC,fact_id DESC) AS rn
                 FROM financial_facts
               ) WHERE rn=1"""
        ).fetchall()
        result = {}
        for row in rows:
            result.setdefault(row["security_id"], {})[row["metric_code"]] = {
                "value": row["value_text"], "unit": row["unit"], "period": row["period"]
            }
        return result

    def snapshots(self):
        return self.connection.execute(
            "SELECT * FROM ranking_snapshots ORDER BY created_at DESC"
        ).fetchall()

    def source_documents(self):
        return self.connection.execute(
            "SELECT * FROM source_documents ORDER BY fetched_at DESC LIMIT 200"
        ).fetchall()

    def ingestion_jobs(self):
        return self.connection.execute(
            "SELECT * FROM ingestion_jobs ORDER BY started_at DESC LIMIT 100"
        ).fetchall()

    def snapshot(self, snapshot_id):
        return self.connection.execute(
            "SELECT * FROM ranking_snapshots WHERE snapshot_id=?", (snapshot_id,)
        ).fetchone()

    def stock(self, snapshot_id, symbol):
        return self.connection.execute(
            """SELECT r.*,s.symbol,s.name,s.market,s.industry,s.model_code
               FROM stock_rankings r JOIN securities s USING(security_id)
               WHERE r.snapshot_id=? AND s.symbol=?""", (snapshot_id, symbol)
        ).fetchone()

    def financial_facts(self, symbol, as_of_date=None):
        sql = """SELECT f.*,s.symbol,d.provider,d.source_key,d.sha256
                 FROM financial_facts f JOIN securities s USING(security_id)
                 JOIN source_documents d USING(source_id) WHERE s.symbol=?"""
        params = [symbol]
        if as_of_date:
            sql += " AND f.available_at<=?"
            params.append(as_of_date)
        sql += " ORDER BY f.metric_code,f.period"
        return self.connection.execute(sql, params).fetchall()

    def rank_history(self, symbol):
        return self.connection.execute(
            """SELECT p.as_of_date,p.status,p.rule_version,r.*
               FROM stock_rankings r JOIN securities s USING(security_id)
               JOIN ranking_snapshots p USING(snapshot_id)
               WHERE s.symbol=? ORDER BY p.as_of_date,p.created_at""", (symbol,)
        ).fetchall()

    def quality_issues(self, unresolved_only=True):
        sql = """SELECT q.*,s.symbol,s.name FROM data_quality_issues q
                 LEFT JOIN securities s USING(security_id)"""
        if unresolved_only:
            sql += " WHERE q.resolved_at IS NULL"
        sql += " ORDER BY CASE severity WHEN 'CRITICAL' THEN 0 WHEN 'WARNING' THEN 1 ELSE 2 END,created_at DESC"
        return self.connection.execute(sql).fetchall()

    def quality_summary(self):
        latest = self.latest_snapshot(status=None)
        if not latest:
            return {"universe": 0, "ranked": 0, "provisional": 0, "critical": 0, "jobs": []}
        snapshot_id = latest["snapshot_id"]
        universe = self.connection.execute(
            "SELECT COUNT(*) FROM securities WHERE valid_to IS NULL"
        ).fetchone()[0]
        ranked = self.connection.execute(
            "SELECT COUNT(*) FROM stock_rankings WHERE snapshot_id=? AND rank_status='RANKED'", (snapshot_id,)
        ).fetchone()[0]
        critical = self.connection.execute(
            "SELECT COUNT(*) FROM data_quality_issues WHERE resolved_at IS NULL AND severity='CRITICAL'"
        ).fetchone()[0]
        jobs = [dict(row) for row in self.connection.execute(
            "SELECT * FROM ingestion_jobs ORDER BY started_at DESC LIMIT 10"
        )]
        return {"universe": universe, "ranked": ranked,
                "provisional": 1 if latest["status"] == "PROVISIONAL" else 0,
                "critical": critical, "jobs": jobs, "snapshot_id": snapshot_id}

    def add_quality_issue(self, snapshot_id, security_id, period, field, severity, code, details, provider):
        self.connection.execute(
            """INSERT INTO data_quality_issues
               (snapshot_id,security_id,period,field,severity,code,details,provider,created_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (snapshot_id, security_id, period, field, severity, code, details, provider,
             datetime.now(timezone.utc).isoformat()),
        )
        self.connection.commit()

    def lineage(self, snapshot_id, symbol, metric_code):
        result = self.connection.execute(
            """SELECT m.*,s.symbol,s.name,p.as_of_date,p.rule_version,p.checksum AS snapshot_checksum
               FROM metric_results m JOIN securities s USING(security_id)
               JOIN ranking_snapshots p USING(snapshot_id)
               WHERE m.snapshot_id=? AND s.symbol=? AND m.metric_code=?""",
            (snapshot_id, symbol, metric_code),
        ).fetchone()
        if not result:
            return None
        facts = self.connection.execute(
            """SELECT f.*,d.provider,d.source_key,d.sha256 FROM financial_facts f
               JOIN source_documents d USING(source_id)
               WHERE f.security_id=? AND f.available_at<=? ORDER BY f.period""",
            (result["security_id"], result["as_of_date"]),
        ).fetchall()
        return {"metric_result": dict(result), "source_facts": [dict(row) for row in facts]}

    def metric_results(self, snapshot_id, symbol):
        return self.connection.execute(
            """SELECT m.* FROM metric_results m JOIN securities s USING(security_id)
               WHERE m.snapshot_id=? AND s.symbol=? ORDER BY m.metric_code""",
            (snapshot_id, symbol),
        ).fetchall()

    def desktop_rankings(self, snapshot_id):
        """Return immutable snapshot rows in the tuple shape consumed by Tk UI."""
        snapshot = self.connection.execute(
            "SELECT status FROM ranking_snapshots WHERE snapshot_id=?", (snapshot_id,)
        ).fetchone()
        if snapshot is None:
            return []
        rows = []
        for row in self.rankings(snapshot_id):
            grades = {item["metric_code"]: item["grade"] for item in self.connection.execute(
                "SELECT metric_code,grade FROM metric_results WHERE snapshot_id=? AND security_id=?",
                (snapshot_id, row["security_id"]),
            )}
            margin_code = {
                "TW4F_FINANCIAL": "PRETAX_MARGIN_FINANCIAL",
                "TW4F_SECURITIES": "OP_MARGIN_SECURITIES",
            }.get(row["model_code"], "OP_MARGIN_GENERAL")
            metric_order = (
                "REV_GROWTH", margin_code, "NET_PROFIT_GROWTH",
                "EPS_TTM", "INVENTORY_TURNOVER_Q", "FCF_CORE",
            )
            expected = 4 if row["model_code"] in {"TW4F_FINANCIAL", "TW4F_SECURITIES"} else 6
            completeness = round(row["valid_count"] * 100 / expected)
            population_key = f'{row["model_code"]}|{row["industry"]}'
            population = self.connection.execute(
                """SELECT eligible_count FROM ranking_populations
                   WHERE snapshot_id=? AND population_type='INDUSTRY' AND population_key=?""",
                (snapshot_id, population_key),
            ).fetchone()
            industry_rank = (str(row["rank_industry"]) if population and population["eligible_count"] >= 10
                             else "樣本不足")
            rows.append((
                row["rank_model"], industry_rank,
                round(float(row["model_percentile"]), 1), row["symbol"], row["name"],
                row["market"], row["industry"], float(row["overall_score"]), completeness,
                tuple(grades.get(code, "N/A") for code in metric_order), snapshot["status"],
            ))
        return rows

    def begin_job(self, provider):
        job_id = str(uuid.uuid4())
        self.connection.execute(
            "INSERT INTO ingestion_jobs(job_id,provider,started_at,status) VALUES(?,?,?,?)",
            (job_id, provider, datetime.now(timezone.utc).isoformat(), "RUNNING"),
        )
        self.connection.commit()
        return job_id

    def finish_job(self, job_id, status, row_count=0, error_text=None):
        self.connection.execute(
            """UPDATE ingestion_jobs SET ended_at=?,status=?,row_count=?,error_text=?
               WHERE job_id=?""",
            (datetime.now(timezone.utc).isoformat(), status, row_count, error_text, job_id),
        )
        self.connection.commit()

    def store_source_and_facts(self, provider, source_key, published_at, version, checksum, facts):
        source_id = hashlib.sha256(f"{provider}|{source_key}|{version}".encode()).hexdigest()
        with self.connection:
            self.connection.execute(
                """INSERT OR IGNORE INTO source_documents
                   (source_id,provider,source_key,published_at,fetched_at,sha256,version)
                   VALUES(?,?,?,?,?,?,?)""",
                (source_id, provider, source_key, published_at,
                 datetime.now(timezone.utc).isoformat(), checksum, version),
            )
            for fact in facts:
                self.connection.execute(
                    """INSERT OR REPLACE INTO financial_facts
                       (security_id,metric_code,period,value_text,published_at,available_at,
                        statement_scope,unit,version,source_id)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (fact["security_id"], fact["metric_code"], fact["period"], fact["value"],
                     fact["published_at"], fact["available_at"], fact["scope"], fact["unit"],
                     fact["version"], source_id),
                )
        return source_id
