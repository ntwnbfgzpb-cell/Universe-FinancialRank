# 原生執行檔建置狀態

目標成品：

- `SixFinancialRank-macOS-AppleSilicon.dmg`：內含可拖入 Applications 的 `.app`
- `SixFinancialRank-Windows-x64.zip`：解壓後雙擊 `SixFinancialRank.exe`

## 已完成

- macOS Apple Silicon 原生建置工作
- Windows x64 單一 EXE 建置工作
- 素材與規則檔封裝
- 無視窗自我測試
- macOS arm64 架構驗證、Developer ID 簽署、公證與 DMG 封裝
- Windows 64-bit 建置環境驗證
- Windows Authenticode SHA-256 簽署與可信時間戳
- GitHub Actions 手動建置與版本標籤建置

## 尚需外部建置環境完成

- 將專案放入 GitHub repository 並執行 `Build native desktop apps`
- 下載兩個 workflow artifacts，於實體 Apple Silicon Mac 與 Windows x64 電腦進行人工啟動驗收
- 在 repository 的 Actions Secrets 設定下列憑證資料後，才能產出正式簽署成品；流程不會建立未簽署的替代成品

## GitHub Actions Secrets

macOS：`APPLE_CERTIFICATE_P12_BASE64`、`APPLE_CERTIFICATE_PASSWORD`、`KEYCHAIN_PASSWORD`、`APPLE_ID`、`APPLE_TEAM_ID`、`APPLE_APP_PASSWORD`。

Windows：`WINDOWS_CERTIFICATE_PFX_BASE64`、`WINDOWS_CERTIFICATE_PASSWORD`。

憑證檔需先轉為單行 Base64，再存入 secret。請勿把 `.p12`、`.pfx` 或密碼提交到 Git。

原生執行檔不可由 Linux 交叉假冒產出；此流程分別使用 GitHub 的 macOS arm64 與 Windows x64 主機建置並檢查成品。
