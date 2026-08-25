# 六大財務指標 Rank｜桌面視窗版

## 執行

一般使用者應下載原生發行檔：macOS 使用 DMG 內的 `.app`；Windows 解壓 ZIP 後雙擊 `.exe`。以下 Python 指令僅供開發者使用。

### Windows

雙擊 run_windows.bat，或執行：

    python desktop_app.py

### macOS

第一次先執行：

    chmod +x run_macos.command

之後雙擊 run_macos.command，或執行：

    python3 desktop_app.py

## 需求

- Python 3.10 以上
- Tkinter
- Pillow

## 已完成

- 原生桌面視窗與左側導覽
- 視窗尺寸保存
- 排行榜搜尋、市場／產業／快照篩選
- 表格欄位排序
- 雙擊個股開啟獨立詳情視窗
- 原生 CSV 儲存對話框
- 星系關聯圖 Canvas
- 3D 排名熱力 Canvas
- 資料品質頁
- 宇宙金融背景素材
- Decimal 六指標評分引擎
- SQLite 不可變快照、checksum 與 metric decision trace
- 桌面視窗內「建立本機快照」
- 視窗內離線 CSV 驗證、匯入、評分與不可變快照
- 匯入後排行榜、個股頁、熱力圖改讀最新本機快照
- 模型／市場／產業各自 DENSE_RANK 與模型內百分位
- stdlib 唯讀本機 API（不額外依賴 FastAPI）
- Windows／macOS PyInstaller 建置腳本
- 證交所 OpenAPI Bronze 原始資料同步與 SHA-256 manifest
- 動態資料品質、來源血緣、排名歷史與規則 API
- Bronze→PARTIAL Silver 證券／月營收自動轉換
- 累計財報單季化、Core FCF 符號正規化與零基期保護
- 歷史不可變快照切換、冪等發布、資料庫備份／驗證／安全還原
- MOPS XBRL 精確 tag 映射、單季化與 Silver 財務事實輸出
- ISIN／統編／代號有效期間、公司行動與規則版本資料層
- 個股排名歷史與完整來源血緣視窗
- OpenAPI 3.0.3 文件與可選排行榜分頁
- TWSE／TPEx／MOPS 官方資料自動取得、降級與每日排程
- 桌面一鍵下載、正規化、評分並建立 PROVISIONAL 快照

## 匯入與 API

欄位與防止未來資訊滲漏規則請見 `IMPORT_FORMAT.md`。範本位於 `import_templates/`。

    python3 import_official.py import_templates --as-of 2026-08-25 --status FINAL
    python3 local_api.py --db ~/.six_financial_rank/rank_local.db

官方原始資料同步：

    python3 sync_official.py
    python3 normalize_bronze.py <bronze-run> <silver-output>

同步後會建立 PARTIAL Silver 包，但不會未經季度 taxonomy 映射直接發布 FINAL 排名。完整端點請見 `API.md`，維運與備份請見 `OPERATIONS.md`。

XBRL 匯入與 manifest 格式請見 `XBRL_IMPORT.md`。
官方來源、安全限制與降級策略請見 `OFFICIAL_SOURCES.md`。

## 目前限制

目前內建資料與範本明確屬於示範資料，並非正式投資研究結果。證交所 OpenAPI 原始同步層已完成；正式上線仍需以真實官方檔完成 Core FCF 現金流欄位、單季化與完整 taxonomy mapping，以及 30 檔逐欄對帳。建置腳本需在目標 Windows/macOS 電腦執行，才能產出並驗證對應平台執行檔。
