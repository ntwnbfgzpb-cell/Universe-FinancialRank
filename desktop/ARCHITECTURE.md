# 架構與資料流

1. Bronze：`TwseOpenApiRawAdapter` 下載 allowlist 資料，逐次保存原始 JSON 與 manifest SHA-256。
2. Silver：`normalize_twse_bronze` 建立證券主檔與月營收事實；季報映射未齊時標記 PARTIAL。
3. Gold：`OfficialImportPipeline` 驗證欄位、日期與模型，以 Decimal 規則引擎產生評等與 decision trace。
4. Snapshot：`LocalRepository.publish_snapshot` 以單一 SQLite 交易發布排名、指標與 population；相同輸入冪等。
5. Delivery：Tkinter 桌面視窗、CSV 匯出及只監聽 localhost 的唯讀 API。

設計決策：單機版避免強制安裝 FastAPI、PostgreSQL、Redis；資料與服務邊界仍保留，日後可將 repository/provider 替換為正式服務端實作。
