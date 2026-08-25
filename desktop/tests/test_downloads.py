import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop.core.downloads import OfficialDownloadError, SwaggerOfficialAdapter, validate_official_url


class DownloadsTests(unittest.TestCase):
    def test_non_official_host_is_rejected(self):
        with self.assertRaises(OfficialDownloadError):
            validate_official_url("https://example.com/data.json")

    def test_swagger_discovers_by_official_summary(self):
        spec = {"basePath":"/openapi","paths":{
            "/company":{"get":{"summary":"上櫃公司基本資料"}},
            "/unrelated":{"get":{"summary":"其他資料"}}
        }}
        adapter = SwaggerOfficialAdapter("https://www.tpex.org.tw/openapi/swagger.json", "/tmp/unused",
                                         ("上櫃公司基本資料",))
        self.assertEqual(adapter.discover(spec), [("/company","上櫃公司基本資料")])

    def test_swagger_sync_keeps_discovery_manifest(self):
        spec = json.dumps({"basePath":"/openapi","paths":{
            "/company":{"get":{"summary":"上櫃公司基本資料"}}
        }}, ensure_ascii=False).encode()
        dataset = json.dumps([{"代號":"1234"}],ensure_ascii=False).encode()
        with tempfile.TemporaryDirectory() as directory, patch(
            "desktop.core.downloads.fetch_bytes", side_effect=[(spec,{}),(dataset,{"Content-Type":"application/json"})]
        ):
            run_dir, manifest = SwaggerOfficialAdapter(
                "https://www.tpex.org.tw/openapi/swagger.json", directory, ("上櫃公司基本資料",)
            ).sync()
            self.assertEqual(manifest["datasets"][0]["rows"], 1)
            self.assertTrue((run_dir/"swagger.json").exists())


if __name__ == "__main__":
    unittest.main()
