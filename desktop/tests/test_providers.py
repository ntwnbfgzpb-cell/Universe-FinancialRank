import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop.core.providers import TwseOpenApiRawAdapter


class FakeResponse:
    headers = {"Content-Type": "application/json"}
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return json.dumps([{"公司代號":"2330"}], ensure_ascii=False).encode()


class ProviderTests(unittest.TestCase):
    def test_raw_sync_keeps_payload_and_manifest_checksum(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            "desktop.core.providers.urlopen", return_value=FakeResponse()
        ):
            run_dir, manifest = TwseOpenApiRawAdapter(directory).sync(["listed_companies"])
            self.assertTrue((run_dir / "listed_companies.json").exists())
            self.assertEqual(manifest["datasets"][0]["rows"], 1)
            self.assertEqual(len(manifest["datasets"][0]["sha256"]), 64)

    def test_unknown_dataset_is_rejected_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                TwseOpenApiRawAdapter(directory).sync(["untrusted_url"])


if __name__ == "__main__":
    unittest.main()
