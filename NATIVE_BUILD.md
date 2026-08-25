# 原生執行檔建置狀態（未使用正式憑證測試版）

目標成品：

- `SixFinancialRank-macOS-AppleSilicon.dmg`：內含可拖入 Applications 的 `.app`
- `SixFinancialRank-Windows-x64.zip`：解壓後雙擊 `SixFinancialRank.exe`

## 已完成

- macOS Apple Silicon 原生建置工作
- Windows x64 單一 EXE 建置工作
- 素材與規則檔封裝
- 無視窗自我測試
- macOS arm64 架構驗證、ad-hoc 簽署與 DMG 封裝
- Windows 64-bit 建置環境驗證
- GitHub Actions 手動建置與版本標籤建置

## 尚需外部建置環境完成

- 將專案放入 GitHub repository 並執行 `Build native desktop apps`
- 下載兩個 workflow artifacts，於實體 Apple Silicon Mac 與 Windows x64 電腦進行人工啟動驗收
- 本版不需要 GitHub Actions Secrets。macOS 未使用 Developer ID、未送 Apple 公證；Windows 未使用 Authenticode 憑證。首次開啟可能顯示安全警告，僅供功能驗收。

原生執行檔不可由 Linux 交叉假冒產出；此流程分別使用 GitHub 的 macOS arm64 與 Windows x64 主機建置並檢查成品。
