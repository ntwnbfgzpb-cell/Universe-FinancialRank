import tempfile
import unittest
from pathlib import Path

from desktop.backup_restore import create_backup, restore_backup, verify_backup
from desktop.core.storage import LocalRepository


class BackupTests(unittest.TestCase):
    def test_rapid_backups_never_reuse_a_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "rank.db"
            LocalRepository(source).close()
            first, _ = create_backup(source, root / "backups")
            second, _ = create_backup(source, root / "backups")
            self.assertNotEqual(first.name, second.name)
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())

    def test_backup_verify_and_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "rank.db"
            repository = LocalRepository(source)
            repository.close()
            backup, _ = create_backup(source, root / "backups")
            manifest = verify_backup(backup)
            self.assertEqual(len(manifest["sha256"]), 64)
            restored = restore_backup(backup, root / "restored.db")
            self.assertTrue(restored.exists())

    def test_restore_refuses_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "rank.db"
            repository = LocalRepository(source)
            repository.close()
            backup, _ = create_backup(source, root / "backups")
            with self.assertRaises(FileExistsError):
                restore_backup(backup, source)


if __name__ == "__main__":
    unittest.main()
