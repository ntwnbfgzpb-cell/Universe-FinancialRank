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

## 驗證結果

- Vite production build：通過
- Python 排名／快照／匯入／XBRL 測試：37/37 通過
- AI PNG 素材已由 Vite 寫入 production assets

## 後續驗收

- 在 GitHub Actions 原生 macOS/Windows runner 完成 Electron Builder 封裝
- 在實體 Apple Silicon Mac 與 Windows x64 測試首次開啟、安全提示、視窗縮放及官方同步
- 正式發行前加入 Developer ID／Authenticode 憑證

本文件反映 React/Electron 新版；舊 Tkinter 版僅保留作為既有資料處理與相容性參考。
