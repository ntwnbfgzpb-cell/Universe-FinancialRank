# MOPS XBRL 匯入

將同一批 XBRL 放在一個目錄，並建立 `manifest.csv`：

    symbol,fiscal_year,quarter,published_at,available_at,scope,version,file
    2330,2025,1,2025-05-10,2025-05-10,CONSOLIDATED,v1,2330_2025Q1.xbrl

執行：

    python3 normalize_xbrl.py ./xbrl ./financial_facts.csv

處理流程：

- 只接受 `config/xbrl_mapping.v1.json` 明列的精確 concept local name。
- 損益、EPS、銷貨成本及現金流累計值轉成單季；資產負債表存貨不相減。
- 產生營業利益率、歸母淨利、淨利 YoY、單季 EPS、未年化存貨週轉與 Core FCF。
- Core FCF 同時扣除 PPE 與無形資產支出，並先正規化現金流出符號。
- 未映射 concept 寫入 `.report.json`，不得模糊比對或自行猜測。

不同年度 taxonomy 若更換 concept，須建立新版 mapping 並重新驗證，不可原地修改已發布快照使用的版本。
