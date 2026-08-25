# Cosmic Finance Asset Inventory

設計比例：明亮金融工作台 85%＋宇宙資料視覺 15%  
狀態：正式素材已生成並完成基本格式／透明度 QA；尚未接入程式。

| 檔案 | 用途 | 尺寸 | 透明 | 使用規則 |
|---|---|---:|---|---|
| bg-financial-ledger-light.png | 主內容區暖白背景 | 1536×1024 | 否 | 低對比使用；表格區可再覆蓋純白 surface |
| bg-cosmic-sidebar-navy.png | 桌機側欄與深色導覽區 | 864×1821 | 否 | 中央導航文字區保持低干擾 |
| overlay-neural-correlation.png | 星系關聯圖的低對比連結底層 | 1672×941 | 是 | 不代表正式節點或因果；實際關係由程式繪製 |
| industry-constellations-sprite.png | 進階星系頁的六種產業星座紋理 | 1536×1024 | 否 | 固定 3×2 裁切；只用於深色進階頁 |
| rank-percentile-orbit.png | 選取節點／百分位焦點光環 | 1536×1024 | 是 | 只標示焦點；百分位仍必須顯示數字 |
| empty-no-snapshot.png | 尚未建立 Rank 快照 | 1378×1141 | 是 | 搭配程式文字與建立快照按鈕 |
| empty-no-filter-results.png | 篩選無結果 | 1448×1086 | 是 | 搭配清除／調整條件操作 |
| empty-lineage-incomplete.png | 資料血緣未齊 | 1603×981 | 是 | 不等同資料錯誤；顯示缺少階段 |
| illustration-immutable-snapshot.png | 不可變快照說明 | 1254×1254 | 是 | 用於說明、快照歷史與治理頁 |
| maintenance-data-source.png | 官方來源同步暫停／維護 | 1448×1086 | 是 | 搭配重試時間、來源名稱與工作狀態 |

## 品質檢查

- 所有透明素材均確認含 RGBA 與實際 0–最大 Alpha 範圍。
- 背景素材為 RGB，避免透明疊色造成閱讀區色偏。
- 素材內不含股票代號、財務數字、交易方向、目標價、公司 Logo 或功能文字。
- 正式 UI 文字、表格、圖表、節點、邊、狀態、圖例和互動控制均需程式原生產生。
- 產業星座 sprite 使用統一深藍背景，避免生成式透明棋盤被烘焙進素材。

## 實作注意

1. 主排行榜只使用暖白背景與深藍側欄；不顯示神經網路覆層。
2. overlay-neural-correlation 只可在進階星系視圖以低透明度使用。
3. 3D 熱力圖的柱體、座標、圖例和密度線由 WebGL／Three.js 即時繪製，不使用靜態圖片替代。
4. 空狀態插圖桌機建議最大顯示寬度 280–360px，手機 180–240px。
5. 尊重 prefers-reduced-motion；軌道素材不可持續高速旋轉。
6. 所有圖片須提供替代文字；純裝飾背景使用空 alt。

## 生成方式

使用內建 AI 圖像生成工具逐項生成；背景、透明覆層、sprite 與空狀態分別使用獨立 prompt，未使用單一大圖裁切冒充多項素材。
