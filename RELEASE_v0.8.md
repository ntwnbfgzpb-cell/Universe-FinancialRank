# v0.8 官方資料自動取得與排程版

## 完成

- TWSE、TPEx、MOPS 多來源官方下載架構。
- TPEx Swagger 動態端點發現，避免依賴易變的硬編碼路徑。
- MOPS 同網域公開 XBRL/XML/ZIP 索引下載；不繞過驗證或安全限制。
- HTTPS 官方網域 allowlist、重試、指數退避、限速、單檔大小上限與 SHA-256。
- TPEx 公司／月營收 Bronze→Silver 合併。
- 月度與季度分批匯入後，使用截至快照日的歷史事實累積重算。
- 一鍵自動更新：下載→Bronze→Silver→XBRL（可選）→Gold→PROVISIONAL 快照。
- 桌面資料品質頁新增「一鍵自動更新暫定榜」。
- 每日排程器與 `--once` 排程測試模式。
- 37 項自動測試通過。

## 外部官方限制

- 本執行環境連 TPEx Swagger 實測回傳 403；程式已提供使用者本機重試與降級。
- MOPS 部分 AJAX 明確回覆安全限制，因此程式只使用直接公開下載檔，不繞過管控。
- FINAL 仍須真實 XBRL taxonomy 校準與 30 檔對帳，不能僅因成功下載就自動核准。
