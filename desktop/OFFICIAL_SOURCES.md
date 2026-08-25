# 官方程式化資料來源

## TWSE

- Base：`https://openapi.twse.com.tw/v1`
- 使用公司主檔、公開發行公司主檔、上市／公開發行月營收，以及各業別損益與資產負債表。
- 端點採程式內 allowlist，不接受任意 URL。

## TPEx

- Swagger：`https://www.tpex.org.tw/openapi/swagger.json`
- 程式每次先讀官方 Swagger，再依 summary 尋找上櫃公司主檔、月營收與上櫃股票資料，不把易變端點寫死。
- 若官方回傳 403／429／格式變更，記錄警告並保留 TWSE 已完成步驟。

## MOPS

- 僅支援使用者指定的官方 MOPS 公開索引頁。
- 只下載同一官方網域直接公開的 `.zip`、`.xbrl`、`.xml`。
- 不呼叫受安全機制保護的 AJAX、不處理驗證碼、不模擬登入、不繞過限制。

## 下載安全與可追溯性

- 只允許 HTTPS 與 `openapi.twse.com.tw`、`www.tpex.org.tw`、`mops.twse.com.tw`。
- 最多重試三次，採指數退避；資料集間主動限速。
- 單檔預設上限 100 MB，索引頁上限 20 MB。
- 保存原始 payload、官方 URL、Content-Type、列數、時間、SHA-256 與 manifest。
- 外部資料預設發布 `PROVISIONAL`；FINAL 必須經 taxonomy、完整度及 reconciliation 檢查。
