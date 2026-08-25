# 即時進度

最後更新：2026-08-25

| 工作 | 狀態 | 證據／下一步 |
|---|---|---|
| 圖片素材與透明度 QA | VERIFIED | 14 組正式素材，含產業星座與 Rank 歷史空狀態 |
| 排行榜、篩選、CSV | DONE | app/index.html、app/app.js |
| 個股詳情與決策軌跡 | DONE | app/app.js |
| 星系關聯圖 | VERIFIED | 真實排名節點，依分數、百分位與產業權重計算關聯邊，可調門檻與檢視個股 |
| 3D 排名熱力圖 | VERIFIED | CSS 3D 即時柱體、真實排名資料、產業篩選、高度指標與 2D／透視切換 |
| 資料品質頁 | VERIFIED | 已串 SQLite 品質摘要、問題清單與匯入工作紀錄 |
| Decimal 六指標規則引擎 | VERIFIED | 規則、邊界、N/A 與平均分測試通過 |
| SQLite 不可變快照 | VERIFIED | checksum、metric trace、ranking persistence 測試通過 |
| DENSE_RANK 與快照原子性 | VERIFIED | 同分 1、1、2 測試；交易內無獨立 commit |
| 官方 CSV adapter 介面 | DONE | desktop/core/providers.py；待實際官方檔驗證 |
| 離線 CSV 匯入管線 | VERIFIED | 欄位／日期／模型驗證、future cutoff、不可變快照測試通過 |
| 桌面匯入後資料串接 | VERIFIED | 排行榜、個股與熱力圖改讀最新快照 |
| 分組排名與模型百分位 | VERIFIED | 模型／市場／產業分組與 DENSE_RANK 測試通過 |
| 唯讀本機 API | VERIFIED | stdlib HTTP API 執行緒 smoke test 通過 |
| Windows／macOS 打包腳本 | DONE | 需在對應目標 OS 執行 PyInstaller 驗證 |
| FastAPI、PostgreSQL | DEFERRED | 正式多人服務端階段；單機版先採 SQLite + stdlib API |
| 證交所 OpenAPI Bronze 同步 | VERIFIED | 14 組 allowlist、原始 JSON、SHA-256 manifest 與 mock 網路測試 |
| Bronze→Silver 月營收串接 | VERIFIED | 公司主檔、普通股候選、月營收 YoY 與 PARTIAL 報告測試 |
| 累計財報單季化與衍生公式 | VERIFIED | Q4、缺季、Core FCF 符號、零庫存及零基期測試 |
| 規則治理與 checksum | VERIFIED | 啟動驗證 rule_id／priority／Decimal，快照保存規則 checksum |
| 歷史快照切換 | DONE | 桌面視窗可依日期、狀態、版本與 checksum 載入 |
| 備份與還原 | VERIFIED | SQLite backup、SHA-256、integrity_check、拒絕意外覆寫 |
| MOPS XBRL→Silver | VERIFIED | 精確 tag、manifest、單季化、衍生六指標與未映射報告測試 |
| 證券生命週期 | VERIFIED | 公司關係、ISIN／統編／代號歷史、公司行動與代號變更測試 |
| OpenAPI 與分頁 | VERIFIED | OpenAPI 3.0.3、page_size 驗證與相容回傳 |
| 個股歷史／血緣視窗 | DONE | 桌面可檢視快照歷史、規則、原始事實與來源 SHA-256 |
| TWSE 自動取得 | VERIFIED | 固定 allowlist、原檔 manifest 與 mock HTTP 測試 |
| TPEx 自動取得 | VERIFIED | Swagger 動態發現、公司／月營收 Silver 合併與 403 降級 |
| MOPS 公開檔下載 | DONE | 同網域公開 ZIP/XBRL/XML；不繞過安全限制 |
| 一鍵更新與每日排程 | DONE | 桌面按鈕、CLI pipeline、PROVISIONAL 預設與 scheduler |
| 跨批次歷史事實累積 | VERIFIED | 依 available_at cutoff 從 SQLite 累積重算 |
| 完整 taxonomy 與 30 檔對帳 | BLOCKED | 需 Core FCF 現金流細項及可連官方站點／真實官方檔 |
| 原生桌面視窗版 | DONE | desktop/desktop_app.py；待有圖形顯示環境完成視覺驗證 |
| React/Electron 全功能頁 | VERIFIED | 已移除所有建置中頁；Vite production build 通過 |
| 官方同步桌面串接 | VERIFIED | POST /api/v1/admin/sync 背景執行完整官方更新管線 |
| 來源與擷取紀錄頁 | VERIFIED | source_documents、ingestion_jobs 與同步狀態 API 已串接 |
| AI 總覽／空狀態素材 | VERIFIED | 2 組新素材已接入程式與素材清冊 |
| 排行榜完整互動 | VERIFIED | 7 類篩選、8 欄排序、實際分頁與本機收藏 |
| 個股研究完整串接 | VERIFIED | 摘要、六指標、財務事實、Rank 歷史與血緣 API |
| Galaxy／熱力圖互動 | VERIFIED | 真實排名節點、篩選、檢視、2D／3D 切換與低負載 Liquid Orb 視覺 |
| 最新六項財務值 | VERIFIED | ranking API 以 window function 取得每公司最新財務事實 |
| 桌面設定與啟動韌性 | VERIFIED | 本機設定、reduced motion、自動刷新與 API 快速重試 |
| 跨模組分頁瀏覽 | VERIFIED | 排行榜、選股、產業、快照、Rank 歷史、血緣、來源與品質清單共用分頁控制 |
| 品質治理五頁籤 | VERIFIED | 新鮮度、異常、工作、Taxonomy 與對帳皆可瀏覽；不再顯示虛構 QA 成績 |
| AI 補充空狀態素材 | VERIFIED | 產業星座與 Rank 歷史軌道圖已生成、透明度檢查並接入程式 |
| 品質摘要真實化 | VERIFIED | 來源新鮮度、文件數、過期來源、問題統計及擷取工作全部讀取 SQLite |
| 星系相似度連線 | VERIFIED | 不使用靜態示意線；由目前快照分數、百分位及產業關係即時計算 |
| Electron 啟動可靠性 | VERIFIED | 健康等待、單一執行個體、後端日誌、外部導覽限制與程序關閉處理 |
| 現代版封裝 smoke test | DONE | Actions 封裝後啟動 API 驗證 health／OpenAPI，並驗證 EXE／DMG 產物 |
| 舊版無作用 UI 清理 | VERIFIED | LegacyRanking、Coming 與未使用控制元件已移除；production build 通過 |

## 驗證紀錄

- JavaScript 語法檢查：通過。
- 本機 HTTP 啟動：通過。
- Playwright：套件可用，但執行環境缺少 Chromium binary，無法完成桌機／手機截圖及概念稿像素比對，因此視覺項目維持 DONE，尚未標 VERIFIED。
- Python：39 項自動測試通過。
- React/Vite production build：通過；所有新增分頁與品質頁籤均完成編譯驗證。
