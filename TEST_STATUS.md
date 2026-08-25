# 測試狀態

最後更新：2026-08-25

| 類別 | 狀態 | 證據 |
|---|---|---|
| Python compile | PASS | desktop_app.py 與 core 模組 |
| 六指標規則單元測試 | PASS | EPS 邊界、營收優先序、營益率、淨利轉正、存貨 1.5、FCF 矩陣 |
| N/A 分母 | PASS | 金融模型存貨與 FCF 不計分 |
| 附件平均分 fixture | PASS | 3+3+1+4+2+0 = 13/6 = 2.17 |
| SQLite 快照 | PASS | checksum、metric trace、ranking persistence |
| DENSE_RANK | PASS | 1、1、2，不跳號 |
| 分組排名 | PASS | 模型／市場／產業各自排名，百分位限於模型內 |
| 快照原子交易 | PASS | 證券主檔 upsert 不在快照交易中自行 commit |
| 離線匯入 | PASS | 完整 CSV 可評分發布；缺檔拒絕 |
| 本機 API | PASS | ThreadingHTTPServer health 跨執行緒請求 |
| 官方 Bronze 同步 | PASS | allowlist、原始 payload、列數與 SHA-256 manifest |
| 動態資料品質 | PASS | 匯入結果可產生品質摘要與問題紀錄 |
| Bronze→Silver | PASS | 公司主檔、普通股候選與月營收 YoY 轉換 |
| 財務轉換 | PASS | Q4 單季化、缺季、FCF 符號、零庫存、零基期 |
| 規則治理 | PASS | checksum、重複 rule_id／priority 阻擋 |
| 冪等發布 | PASS | 相同輸入重跑回傳同一 snapshot_id |
| 備份還原 | PASS | SHA-256、SQLite integrity_check、安全覆寫保護 |
| XBRL 正規化 | PASS | 精確 tag、Q4 單季化、FCF、manifest 必填與未映射報告 |
| 證券生命週期 | PASS | ISIN／統編、代號有效期與代號變更歷史 |
| OpenAPI 文件 | PASS | 本機 API 輸出 OpenAPI 3.0.3 |
| 官方下載安全 | PASS | HTTPS 官方網域 allowlist、非官方 URL 阻擋 |
| TPEx Swagger 發現 | PASS | summary 動態選擇與 manifest 留存 |
| TPEx Silver 合併 | PASS | 上櫃公司與月營收合併至匯入包 |
| 桌面整合 smoke | PASS | 模組匯入與重算入口存在 |
| GUI 視覺自動化 | BLOCKED | 執行容器無圖形顯示伺服器 |
| 官方 30 檔對帳 | BLOCKED | 需官方資料網路或使用者提供真實匯入檔 |

執行全部測試：

    PYTHONPATH=. python3 -m unittest discover -s desktop/tests -v
