from __future__ import annotations

import argparse
import csv
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    from .core import LocalRepository
except ImportError:
    from core import LocalRepository


class ApiHandler(BaseHTTPRequestHandler):
    repository_path: str

    def _json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False, default=dict).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
        self.end_headers()
        self.wfile.write(data)

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
            "/api/v1/export/rankings.csv":"排行榜 CSV", "/api/v1/admin/data-quality":"資料品質"
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
