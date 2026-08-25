import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

from desktop.local_api import ApiHandler


class ApiTests(unittest.TestCase):
    def test_cors_preflight_allows_packaged_electron_json_posts(self):
        with tempfile.TemporaryDirectory() as directory:
            ApiHandler.repository_path = str(Path(directory) / "rank.db")
            server = ThreadingHTTPServer(("127.0.0.1", 0), ApiHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                request = Request(f"http://127.0.0.1:{server.server_port}/api/v1/admin/sync",
                                  method="OPTIONS", headers={"Origin":"null",
                                  "Access-Control-Request-Method":"POST",
                                  "Access-Control-Request-Headers":"content-type"})
                with urlopen(request) as response:
                    self.assertEqual(response.status, 204)
                    self.assertIn("POST", response.headers["Access-Control-Allow-Methods"])
                    self.assertEqual(response.headers["Access-Control-Allow-Headers"], "Content-Type")
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_backup_api_creates_lists_and_restores_verified_database(self):
        with tempfile.TemporaryDirectory() as directory:
            ApiHandler.repository_path = str(Path(directory) / "rank.db")
            ApiHandler.sync_state = {"status":"IDLE","progress":0,"message":"test","report":None}
            server = ThreadingHTTPServer(("127.0.0.1", 0), ApiHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}/api/v1/admin/backups"
                request = Request(base, data=json.dumps({"action":"create"}).encode(),
                                  headers={"Content-Type":"application/json"}, method="POST")
                with urlopen(request) as response:
                    created = json.load(response)
                with urlopen(base) as response:
                    backups = json.load(response)
                self.assertEqual(backups[0]["backup_id"], created["backup_id"])
                self.assertTrue(backups[0]["verified"])
                restore = Request(base, data=json.dumps({"action":"restore", "backup_id":created["backup_id"],
                                  "confirmation":"RESTORE"}).encode(), headers={"Content-Type":"application/json"}, method="POST")
                with urlopen(restore) as response:
                    restored = json.load(response)
                self.assertIn("safety_backup_id", restored)
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_health_endpoint_works_across_request_thread(self):
        with tempfile.TemporaryDirectory() as directory:
            ApiHandler.repository_path = str(Path(directory) / "rank.db")
            server = ThreadingHTTPServer(("127.0.0.1", 0), ApiHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with urlopen(f"http://127.0.0.1:{server.server_port}/api/v1/health") as response:
                    payload = json.load(response)
                self.assertEqual(payload["status"], "ok")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_rules_and_quality_endpoints_are_connected(self):
        with tempfile.TemporaryDirectory() as directory:
            ApiHandler.repository_path = str(Path(directory) / "rank.db")
            server = ThreadingHTTPServer(("127.0.0.1", 0), ApiHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                with urlopen(base + "/api/v1/rules") as response:
                    rules = json.load(response)
                with urlopen(base + "/api/v1/admin/data-quality") as response:
                    quality = json.load(response)
                with urlopen(base + "/api/v1/admin/sources") as response:
                    sources = json.load(response)
                with urlopen(base + "/api/v1/admin/sync") as response:
                    sync = json.load(response)
                with urlopen(base + "/api/v1/openapi.json") as response:
                    openapi = json.load(response)
                self.assertEqual(rules["version"], "TW-RANK-SPEC-v1.2")
                self.assertEqual(quality["summary"]["universe"], 0)
                self.assertEqual(sources, {"documents": [], "jobs": []})
                self.assertIn(sync["status"], {"IDLE", "SUCCESS", "FAILED"})
                self.assertEqual(openapi["openapi"], "3.0.3")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
