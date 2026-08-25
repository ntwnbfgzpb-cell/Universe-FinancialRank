# Universe FinancialRank 現代桌面版重構狀態

## 已完成

- React + Vite + Electron 桌面架構
- 深藍、金色、白底高密度金融設計系統
- AI 宇宙側欄、金融帳冊底紋與神經關聯素材封裝
- 臺股基本面排行榜、完整篩選、排序視覺、選取與分頁
- 排名洞察、產業分布、六指標雷達與財務等級分布
- 個股研究摘要、財務趨勢、決策追蹤、原始期間數值與資料血緣
- 資料品質、來源新鮮度、異常佇列、重算進度、工作紀錄與對帳覆蓋率
- 星系關聯圖
- 3D 排名熱力圖
- 本機 API 健康檢查與最新不可變快照偵測
- Electron 封裝自動啟動 Python/SQLite 本機資料引擎
- macOS Apple Silicon 與 Windows x64 未簽章建置工作流程
- AI 生成「六柱排名＋星系軌道」正式程式圖示，含 PNG／ICO／ICNS 建置流程
- AI 生成總覽星系觀測背景與選股清單透明望遠鏡元件，並正式接入程式
- 原「建置中」頁面已全部實作：總覽、選股清單、產業、快照、規則、來源與教學
- 排行榜、快照切換、個股摘要與六指標改為本機 API 優先；API 不可用時清楚降級為展示模式
- 選股清單使用本機持久化、排行榜 CSV 直接匯出目前快照
- 桌面 UI 可啟動 TWSE／TPEx 官方公開資料同步，背景執行 Bronze→Silver→評分→PROVISIONAL 快照
- 新增來源文件、擷取工作與同步狀態 API，保留官方來源 SHA-256 與工作紀錄

## 驗證結果

- Vite production build：通過
- Python 排名／快照／匯入／XBRL／來源 API 測試：37/37 通過
- AI PNG 素材已由 Vite 寫入 production assets

## 發行前仍需的外部驗收

- 在實體 Apple Silicon Mac 與 Windows x64 測試首次開啟、安全提示、視窗縮放及官方同步
- 正式發行前加入 Developer ID／Authenticode 憑證

本文件反映 React/Electron 新版；舊 Tkinter 版僅保留作為既有資料處理與相容性參考。
