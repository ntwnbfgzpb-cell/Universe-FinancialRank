from __future__ import annotations

import argparse
import csv
import io
import json
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    from .core import LocalRepository
    from .auto_update import run_update
    from .backup_restore import create_backup, restore_backup, verify_backup
except ImportError:
    from core import LocalRepository
    from auto_update import run_update
    from backup_restore import create_backup, restore_backup, verify_backup


class ApiHandler(BaseHTTPRequestHandler):
    repository_path: str
    sync_state = {"status": "IDLE", "progress": 0, "message": "尚未執行同步", "report": None}
    sync_lock = threading.Lock()

    def _json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False, default=dict).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        # Read-only loopback API: allow the packaged Electron file:// origin and
        # local Vite preview to consume responses without weakening network scope.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _csv(self, rows, filename="rankings.csv"):
        output = io.StringIO()
        fields = list(rows[0].keys()) if rows else ["snapshot_id"]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        data = output.getvalue().encode("utf-8-sig")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _error(self, code, message, status=400, details=None):
        return self._json({"error":{"code":code,"message":message,"details":details}}, status)

    def _openapi(self):
        paths = {path:{"get":{"summary":summary,"responses":{"200":{"description":"OK"}}}}
                 for path,summary in {
            "/api/v1/health":"健康狀態", "/api/v1/snapshots":"快照清單",
            "/api/v1/rankings":"排行榜與篩選", "/api/v1/stocks/{symbol}":"個股摘要",
            "/api/v1/stocks/{symbol}/metrics":"指標與決策軌跡",
            "/api/v1/stocks/{symbol}/financials":"財務事實",
            "/api/v1/stocks/{symbol}/rank-history":"排名歷史", "/api/v1/rules":"規則版本",
            "/api/v1/lineage/{snapshot_id}/{symbol}/{metric_code}":"資料血緣",
            "/api/v1/export/rankings.csv":"排行榜 CSV", "/api/v1/admin/data-quality":"資料品質",
            "/api/v1/admin/sources":"來源與工作紀錄", "/api/v1/admin/sync":"官方資料同步"
            , "/api/v1/admin/backups":"本機備份、驗證與還原"
        }.items()}
        return {"openapi":"3.0.3","info":{"title":"六大財務指標 Rank Local API","version":"0.7"},
                "servers":[{"url":"http://127.0.0.1:8765"}],"paths":paths}

    def do_GET(self):
        repository = LocalRepository(self.repository_path)
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/api/v1/health":
                return self._json({"status":"ok","service":"tw-rank-local-api"})
            if parsed.path == "/api/v1/openapi.json":
                return self._json(self._openapi())
            if parsed.path == "/api/v1/snapshots":
                return self._json([dict(row) for row in repository.snapshots()])
            if parsed.path in {"/api/v1/rankings", "/api/v1/export/rankings.csv"}:
                query = parse_qs(parsed.query)
                snapshot_id = query.get("snapshot_id", [None])[0]
                if not snapshot_id:
                    latest = repository.latest_snapshot()
                    if not latest:
                        return self._error("NO_FINAL_SNAPSHOT", "目前沒有 FINAL 快照", 404)
                    snapshot_id = latest["snapshot_id"]
                rows = [dict(row) for row in repository.rankings(snapshot_id)]
                latest_facts = repository.latest_facts_by_security()
                for row in rows:
                    facts = latest_facts.get(row["security_id"], {})
                    row["financial_values"] = {
                        "revenue": facts.get("REVENUE"),
                        "operating_margin": facts.get("OP_MARGIN"),
                        "net_profit": facts.get("NET_PROFIT"),
                        "eps": facts.get("EPS"),
                        "inventory_turnover": facts.get("INVENTORY_TURNOVER_Q"),
                        "free_cash_flow": facts.get("FCF_CORE"),
                    }
                keyword = query.get("q", [""])[0].strip()
                market = query.get("market", [""])[0]
                industry = query.get("industry", [""])[0]
                model = query.get("model", [""])[0]
                rank_status = query.get("rank_status", [""])[0]
                if keyword:
                    rows = [row for row in rows if keyword in row["symbol"] or keyword in row["name"]]
                if market:
                    rows = [row for row in rows if row["market"] == market]
                if industry:
                    rows = [row for row in rows if row["industry"] == industry]
                if model:
                    rows = [row for row in rows if row["model_code"] == model]
                if rank_status:
                    rows = [row for row in rows if row["rank_status"] == rank_status]
                if parsed.path.endswith(".csv"):
                    return self._csv(rows)
                if "page" in query or "page_size" in query:
                    try:
                        page = int(query.get("page", ["1"])[0])
                        page_size = int(query.get("page_size", ["50"])[0])
                    except ValueError:
                        return self._error("INVALID_PAGINATION", "page 與 page_size 必須是整數")
                    if page < 1 or not 1 <= page_size <= 200:
                        return self._error("INVALID_PAGINATION", "page >= 1 且 page_size 必須介於 1 至 200")
                    total = len(rows); start = (page-1)*page_size
                    return self._json({"items":rows[start:start+page_size],
                        "pagination":{"page":page,"page_size":page_size,"total":total,
                                      "pages":(total+page_size-1)//page_size}})
                return self._json(rows)
            if parsed.path == "/api/v1/admin/data-quality":
                return self._json({"summary": repository.quality_summary(),
                                   "issues": [dict(row) for row in repository.quality_issues()]})
            if parsed.path == "/api/v1/admin/sources":
                return self._json({"documents": [dict(row) for row in repository.source_documents()],
                                   "jobs": [dict(row) for row in repository.ingestion_jobs()]})
            if parsed.path == "/api/v1/admin/sync":
                return self._json(dict(self.sync_state))
            if parsed.path == "/api/v1/admin/backups":
                backup_directory = Path(self.repository_path).parent / "backups"
                backups = []
                for backup in sorted(backup_directory.glob("rank_local_*.db"), reverse=True)[:50]:
                    try:
                        manifest = verify_backup(backup)
                        backups.append({"backup_id": backup.name, "created_at": manifest["created_at"],
                                        "sha256": manifest["sha256"], "snapshots": len(manifest.get("snapshots", [])),
                                        "size": backup.stat().st_size, "verified": True})
                    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
                        backups.append({"backup_id": backup.name, "verified": False, "error": str(error),
                                        "size": backup.stat().st_size})
                return self._json(backups)
            if parsed.path == "/api/v1/rules":
                rules_file = Path(__file__).parent / "config" / "rules.v1.2.json"
                return self._json(json.loads(rules_file.read_text(encoding="utf-8")))
            if parsed.path.startswith("/api/v1/lineage/"):
                parts = parsed.path.split("/")
                if len(parts) != 7:
                    return self._error("INVALID_LINEAGE_PATH", "血緣路徑需要 snapshot、symbol、metric", 400)
                lineage = repository.lineage(parts[4], parts[5], parts[6])
                return self._json(lineage if lineage else {"error":"NOT_FOUND"}, 200 if lineage else 404)
            if parsed.path.startswith("/api/v1/stocks/") and parsed.path.endswith("/financials"):
                symbol = parsed.path.split("/")[4]
                query = parse_qs(parsed.query)
                return self._json([dict(row) for row in repository.financial_facts(
                    symbol, query.get("as_of_date", [None])[0])])
            if parsed.path.startswith("/api/v1/stocks/") and parsed.path.endswith("/rank-history"):
                symbol = parsed.path.split("/")[4]
                return self._json([dict(row) for row in repository.rank_history(symbol)])
            if parsed.path.startswith("/api/v1/stocks/") and parsed.path.endswith("/metrics"):
                symbol = parsed.path.split("/")[4]
                query = parse_qs(parsed.query)
                snapshot_id = query.get("snapshot_id", [None])[0]
                if not snapshot_id:
                    latest = repository.latest_snapshot()
                    if not latest:
                        return self._error("NO_FINAL_SNAPSHOT", "目前沒有 FINAL 快照", 404)
                    snapshot_id = latest["snapshot_id"]
                return self._json([dict(row) for row in repository.metric_results(snapshot_id, symbol)])
            if parsed.path.startswith("/api/v1/stocks/"):
                symbol = parsed.path.split("/")[4]
                query = parse_qs(parsed.query)
                snapshot_id = query.get("snapshot_id", [None])[0]
                latest = repository.snapshot(snapshot_id) if snapshot_id else repository.latest_snapshot()
                if not latest:
                    return self._error("NO_FINAL_SNAPSHOT", "目前沒有 FINAL 快照", 404)
                row = repository.stock(latest["snapshot_id"], symbol)
                return self._json(dict(row) if row else {"error":"NOT_FOUND"}, 200 if row else 404)
            return self._error("NOT_FOUND", "找不到指定端點", 404)
        finally:
            repository.close()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/v1/admin/sync", "/api/v1/admin/backups"}:
            return self._error("NOT_FOUND", "找不到指定端點", 404)
        length = int(self.headers.get("Content-Length", "0") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._error("INVALID_JSON", "同步參數不是有效 JSON")
        if parsed.path == "/api/v1/admin/backups":
            if self.sync_state["status"] == "RUNNING":
                return self._error("SYNC_RUNNING", "資料同步期間不可備份或還原", 409)
            action = body.get("action", "create")
            database = Path(self.repository_path)
            backup_directory = database.parent / "backups"
            if action == "create":
                try:
                    if not database.exists():
                        LocalRepository(database).close()
                    backup, manifest_path = create_backup(database, backup_directory)
                    manifest = verify_backup(backup, manifest_path)
                    return self._json({"message":"備份與完整性驗證完成", "backup_id":backup.name,
                                       "created_at":manifest["created_at"], "sha256":manifest["sha256"],
                                       "snapshots":len(manifest.get("snapshots", []))}, 201)
                except (OSError, ValueError) as error:
                    return self._error("BACKUP_FAILED", str(error), 500)
            if action == "restore":
                backup_id = body.get("backup_id", "")
                if body.get("confirmation") != "RESTORE":
                    return self._error("RESTORE_CONFIRMATION_REQUIRED", "還原必須提供 confirmation=RESTORE")
                if not backup_id or Path(backup_id).name != backup_id or not backup_id.startswith("rank_local_") or not backup_id.endswith(".db"):
                    return self._error("INVALID_BACKUP_ID", "備份識別碼無效")
                backup = backup_directory / backup_id
                if not backup.exists():
                    return self._error("BACKUP_NOT_FOUND", "找不到指定備份", 404)
                try:
                    safety_backup, _ = create_backup(database, backup_directory)
                    restore_backup(backup, database, force=True)
                    return self._json({"message":"資料庫已還原；請重新整理程式", "backup_id":backup_id,
                                       "safety_backup_id":safety_backup.name})
                except (OSError, ValueError) as error:
                    return self._error("RESTORE_FAILED", str(error), 500)
            return self._error("INVALID_BACKUP_ACTION", "action 僅能為 create 或 restore")

        publish_status = body.get("status", "PROVISIONAL")
        if publish_status not in {"PROVISIONAL", "FINAL"}:
            return self._error("INVALID_STATUS", "status 僅能為 PROVISIONAL 或 FINAL")
        with self.sync_lock:
            if self.sync_state["status"] == "RUNNING":
                return self._error("SYNC_RUNNING", "官方資料同步已在執行", 409)
            self.sync_state.update(status="RUNNING", progress=5, message="準備連線官方公開資料", report=None)

        def worker():
            try:
                database = Path(self.repository_path)
                self.sync_state.update(progress=15, message="下載 TWSE／TPEx 官方公開資料")
                report = run_update(
                    database,
                    database.parent / "official_pipeline",
                    date.today().isoformat(),
                    publish_status,
                )
                self.sync_state.update(status="SUCCESS", progress=100, message="同步、正規化、評分與快照建立完成", report=report)
            except Exception as error:
                self.sync_state.update(status="FAILED", progress=0, message=str(error), report=None)

        threading.Thread(target=worker, daemon=True).start()
        return self._json(dict(self.sync_state), 202)

    def log_message(self, format, *args):
        return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default=str(Path(__file__).parent / "data" / "rank_local.db"))
    args = parser.parse_args()
    ApiHandler.repository_path = args.db
    server = ThreadingHTTPServer((args.host, args.port), ApiHandler)
    print(f"Local API: http://{args.host}:{args.port}/api/v1/health")
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
