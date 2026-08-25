# 離線官方資料匯入格式

桌面程式的「匯入官方 CSV」會讀取同一資料夾內的兩個 UTF-8 CSV：

- `securities.csv`：證券主檔。
- `financial_facts.csv`：已從公告來源整理、且帶公告／可用日期的財務事實。

## securities.csv

必要欄位：`symbol,name,market,industry,model_code`

- `market`：`上市` 或 `上櫃`。
- `model_code`：`TW6F_GENERAL`、`TW4F_FINANCIAL`、`TW4F_SECURITIES`。

## financial_facts.csv

必要欄位：`symbol,metric_code,period,value,published_at,available_at,scope,unit,version,source_key`

可用指標：`REVENUE_YOY`、`OP_MARGIN`、`NET_PROFIT`、`NET_PROFIT_YOY`、`EPS`、`INVENTORY_TURNOVER_Q`、`FCF_CORE`。

- 日期格式為 `YYYY-MM-DD`；晚於快照日的 `available_at` 不會進入該快照，避免未來資訊滲漏。
- 數值以原始精度匯入，評等前不先四捨五入。
- 一般產業完整評分需要 6 期營收、4 季營業利益率／淨利／EPS／存貨週轉，以及 6 季自由現金流。
- 金融／證券模型不採存貨週轉與自由現金流，完整度分母為 4。

`import_templates/` 是格式示例，內容不是官方資料，也不能當成投資研究結果。

命令列匯入：

    python3 import_official.py import_templates --as-of 2026-08-25 --status FINAL

啟動唯讀本機 API：

    python3 local_api.py --db ~/.six_financial_rank/rank_local.db

端點：`/api/v1/health`、`/api/v1/snapshots`、`/api/v1/rankings`、`/api/v1/stocks/{symbol}/metrics`。
