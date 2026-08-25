# 維運、備份與還原

同步 Bronze：

    python3 sync_official.py

Bronze 轉 PARTIAL Silver：

    python3 normalize_bronze.py <bronze-run> <silver-output> --available-at 2026-08-25

匯入經核驗 Silver／官方 CSV：

    python3 import_official.py <csv-directory> --as-of 2026-08-25 --status FINAL

備份、驗證與還原：

    python3 backup_restore.py create ~/.six_financial_rank/rank_local.db ./backups
    python3 backup_restore.py verify ./backups/rank_local_YYYYMMDDTHHMMSSZ.db
    python3 backup_restore.py restore <backup.db> <new-target.db>

還原預設拒絕覆寫既有資料庫。確認目標與備份 checksum 後，才可使用 `--force`。

一鍵官方更新（預設 PROVISIONAL）：

    python3 auto_update.py --as-of 2026-08-25

加入已合法公開的 MOPS 下載索引與本機 XBRL：

    python3 auto_update.py --mops-index <official-mops-https-url> --xbrl-directory <xbrl-dir>

每日排程或單次排程測試：

    python3 scheduler.py --time 19:30
    python3 scheduler.py --once
