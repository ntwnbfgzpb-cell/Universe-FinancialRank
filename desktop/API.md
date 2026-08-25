# 本機唯讀 API

啟動：

    python3 local_api.py --db ~/.six_financial_rank/rank_local.db --port 8765

主要端點：

- `GET /api/v1/health`
- `GET /api/v1/openapi.json`
- `GET /api/v1/snapshots`
- `GET /api/v1/rankings?market=上市&industry=半導體&model=TW6F_GENERAL`
- `GET /api/v1/export/rankings.csv?snapshot_id=...`
- `GET /api/v1/stocks/{symbol}`
- `GET /api/v1/stocks/{symbol}/metrics`
- `GET /api/v1/stocks/{symbol}/financials?as_of_date=YYYY-MM-DD`
- `GET /api/v1/stocks/{symbol}/rank-history`
- `GET /api/v1/rules`
- `GET /api/v1/lineage/{snapshot_id}/{symbol}/{metric_code}`
- `GET /api/v1/admin/data-quality`

排行榜只有在傳入 `page` 或 `page_size` 時改以 `items + pagination` envelope 回傳；`page_size` 限制為 1～200。未傳分頁參數時維持陣列格式，供既有單機客戶端相容使用。

服務預設只監聽 `127.0.0.1`。若改成可被區網存取，應另加驗證、TLS、速率限制與權限控管。
