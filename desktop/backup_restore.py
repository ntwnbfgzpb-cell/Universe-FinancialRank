from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def create_backup(database, output_directory):
    database, output = Path(database), Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = output / f"rank_local_{stamp}.db"
    source = sqlite3.connect(database)
    destination = sqlite3.connect(backup)
    try:
        source.backup(destination)
        snapshots = [dict(zip([c[0] for c in cursor.description], row)) for cursor in [
            destination.execute("SELECT snapshot_id,as_of_date,status,checksum FROM ranking_snapshots ORDER BY created_at")
        ] for row in cursor.fetchall()]
    finally:
        destination.close()
        source.close()
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "database": backup.name,
                "sha256": sha256(backup), "snapshots": snapshots}
    manifest_path = backup.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return backup, manifest_path


def verify_backup(backup, manifest_path=None):
    backup = Path(backup)
    manifest_path = Path(manifest_path) if manifest_path else backup.with_suffix(".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sha256(backup) != manifest["sha256"]:
        raise ValueError("備份 SHA-256 不相符")
    connection = sqlite3.connect(backup)
    try:
        check = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if check != "ok":
            raise ValueError(f"SQLite integrity_check 失敗：{check}")
    finally:
        connection.close()
    return manifest


def restore_backup(backup, target, force=False):
    verify_backup(backup)
    target = Path(target)
    if target.exists() and not force:
        raise FileExistsError("目標資料庫已存在；確認後使用 --force")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, target)
    return target


def main():
    parser = argparse.ArgumentParser(description="六大財務指標 Rank 備份與還原")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("database")
    create.add_argument("output")
    verify = sub.add_parser("verify")
    verify.add_argument("backup")
    restore = sub.add_parser("restore")
    restore.add_argument("backup")
    restore.add_argument("target")
    restore.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.command == "create":
        print(create_backup(args.database, args.output)[0])
    elif args.command == "verify":
        print(json.dumps(verify_backup(args.backup), ensure_ascii=False, indent=2))
    else:
        print(restore_backup(args.backup, args.target, args.force))


if __name__ == "__main__":
    main()
