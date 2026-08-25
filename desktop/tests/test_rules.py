import json
import tempfile
import unittest
from pathlib import Path

from desktop.core.rules import RuleConfigurationError, load_rule_manifest


class RuleManifestTests(unittest.TestCase):
    def test_manifest_is_valid_and_checksummed(self):
        manifest = load_rule_manifest()
        self.assertEqual(manifest["version"], "TW-RANK-SPEC-v1.2")
        self.assertEqual(len(manifest["checksum"]), 64)

    def test_duplicate_rule_id_is_rejected(self):
        manifest = load_rule_manifest()
        manifest.pop("checksum")
        manifest["rules"].append(dict(manifest["rules"][0], priority=999))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rules.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(RuleConfigurationError):
                load_rule_manifest(path)


if __name__ == "__main__":
    unittest.main()
