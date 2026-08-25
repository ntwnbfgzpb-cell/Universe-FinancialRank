# Universe FinancialRank 現代桌面版

## 開發預覽

```bash
npm install
npm run dev
```

## Production build

```bash
npm run build
```

## 原生執行檔

- Apple Silicon Mac：`npm run dist:mac`
- Windows x64：`npm run dist:win`

發行工作會先將 `desktop/local_api.py` 與 SQLite 排名引擎封裝至 `backend/rank-local-api`，Electron 啟動時在 loopback `127.0.0.1:8765` 自動啟動唯讀 API。使用者資料庫保存於作業系統的 App userData 目錄。

本版使用 AI 生成的宇宙金融背景與神經關聯素材；所有表格、文字、篩選、圖表與互動均為程式原生元件。
