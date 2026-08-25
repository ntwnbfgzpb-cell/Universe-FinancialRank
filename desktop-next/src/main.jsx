import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BarChart3,
  Trophy,
  ListChecks,
  Search,
  Orbit,
  Box,
  Database,
  ShieldCheck,
  History,
  BookOpen,
  Settings,
  Download,
  RefreshCw,
  ChevronDown,
  Star,
  LayoutDashboard,
  Factory,
  SlidersHorizontal,
  Plus,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  CircleHelp,
  GitBranch,
} from "lucide-react";
import { metrics, stocks, months, revenue, yoy } from "./data";
import "./styles.css";

const nav = [
  ["dashboard", "總覽儀表板", LayoutDashboard],
  ["rank", "總體排名", Trophy],
  ["watch", "選股清單", ListChecks],
  ["stock", "個股研究", Search],
  ["industry", "產業研究", Factory],
  ["galaxy", "星系關聯圖", Orbit],
  ["heat", "3D 排名熱力圖", Box],
  ["snapshots", "資料快照", Database],
  ["quality", "資料品質", ShieldCheck],
  ["rules", "規則版本", History],
  ["sources", "資料來源", Database],
  ["help", "使用教學", BookOpen],
];
const gradeClass = (g) => "grade g-" + g.replace("/", "");

function App() {
  const [page, setPage] = useState("rank");
  const [selected, setSelected] = useState("2308");
  const [backend, setBackend] = useState({ connected: false, snapshot: null });
  useEffect(() => {
    let active = true;
    Promise.all([
      fetch("http://127.0.0.1:8765/api/v1/health").then((response) => {
        if (!response.ok) throw new Error("API unavailable");
        return response.json();
      }),
      fetch("http://127.0.0.1:8765/api/v1/snapshots").then((response) =>
        response.json(),
      ),
    ])
      .then(([, snapshots]) => {
        if (active)
          setBackend({ connected: true, snapshot: snapshots?.[0] ?? null });
      })
      .catch(() => active && setBackend({ connected: false, snapshot: null }));
    return () => {
      active = false;
    };
  }, []);
  return (
    <div className="appShell">
      <Sidebar page={page} setPage={setPage} />
      <div className="appMain">
        <Topbar backend={backend} />
        <main>
          {page === "rank" && (
            <Ranking
              selected={selected}
              setSelected={setSelected}
              openStock={() => setPage("stock")}
            />
          )}{" "}
          {page === "stock" && <StockResearch />}
          {page === "quality" && <Quality />}
          {page === "galaxy" && <Galaxy />}
          {page === "heat" && <Heatmap />}
          {!["rank", "stock", "quality", "galaxy", "heat"].includes(page) && (
            <Coming title={nav.find((x) => x[0] === page)?.[1]} />
          )}
        </main>
      </div>
    </div>
  );
}
function Sidebar({ page, setPage }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <BarChart3 />
        <span>
          六大財務指標 <b>Rank</b>
        </span>
      </div>
      <nav>
        {nav.map(([id, label, Icon]) => (
          <button
            key={id}
            className={page === id ? "active" : ""}
            onClick={() => setPage(id)}
          >
            <Icon />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <div className="constellation">
        <i />
        <i />
        <i />
        <i />
        <i />
        <i />
      </div>
      <button className="settings">
        <Settings />
        設定
      </button>
    </aside>
  );
}
function Topbar({ backend }) {
  const snapshotText = backend.snapshot
    ? `${backend.snapshot.as_of_date} ${backend.snapshot.status}`
    : "2026-08-24 FINAL";
  return (
    <header className="topbar">
      <button className="snapshot">
        {snapshotText} <ChevronDown />
      </button>
      <div className="topMeta">
        資料日期：2026-08-24 <CircleHelp />
        <span className={backend.connected ? "synced" : "offline"}>
          {backend.connected ? <CheckCircle2 /> : <AlertTriangle />}
          {backend.connected
            ? "本機資料引擎已連線"
            : "展示模式｜等待本機資料引擎"}
        </span>
        <button>
          <Download />
          匯出資料
        </button>
      </div>
    </header>
  );
}
const Select = ({ label, children }) => (
  <label className="field">
    <span>{label}</span>
    <button>
      {children}
      <ChevronDown />
    </button>
  </label>
);
function Ranking({ selected, setSelected, openStock }) {
  const [q, setQ] = useState("");
  const [market, setMarket] = useState("全部");
  const rows = useMemo(
    () =>
      stocks.filter(
        (s) =>
          (market === "全部" || s[5] === market) &&
          (!q || s[3].includes(q) || s[4].includes(q)),
      ),
    [q, market],
  );
  return (
    <section className="page rankPage">
      <div className="pageTitle">
        <h1>臺股基本面排行榜</h1>
        <button className="filterSaved">
          <SlidersHorizontal />
          篩選條件（已套用 5）
          <ChevronDown />
        </button>
      </div>
      <div className="filterPanel">
        <label className="field searchField">
          <span>股號／名稱</span>
          <div>
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="輸入股號或名稱"
            />
            <Search />
          </div>
        </label>
        <label className="field">
          <span>市場</span>
          <div className="segments">
            {["全部", "上市", "上櫃"].map((x) => (
              <button
                className={market === x ? "on" : ""}
                onClick={() => setMarket(x)}
              >
                {x}
              </button>
            ))}
          </div>
        </label>
        <Select label="產業">全部產業</Select>
        <Select label="模型">六大財務指標</Select>
        <label className="field">
          <span>綜合分數</span>
          <div className="range">
            <input placeholder="最小" />
            <em>~</em>
            <input placeholder="最大" />
          </div>
        </label>
        <Select label="完整度">全部</Select>
        <div className="gradeFilter">
          <b>財務等級（綜合）</b>
          {["全部", "AA", "A", "BB", "B", "C", "N/A"].map((x, i) => (
            <label>
              <input type="checkbox" defaultChecked={i === 0} />
              {x}
            </label>
          ))}
        </div>
        <div className="more">
          <button>
            <Plus />
            新增條件
          </button>
        </div>
        <div className="filterActions">
          <button>清除</button>
          <button className="primary">套用條件</button>
        </div>
      </div>
      <div className="rankWorkspace">
        <div className="tablePanel">
          <table>
            <thead>
              <tr>
                {[
                  "",
                  "模型排名",
                  "同業排名",
                  "百分位",
                  "代號",
                  "名稱",
                  "市場",
                  "產業",
                  "綜合分數",
                  "完整度",
                  "營收(億)",
                  "營益率(%)",
                  "淨利(億)",
                  "EPS(元)",
                  "存貨週轉(次)",
                  "自由現金流(億)",
                  "狀態",
                ].map((x) => (
                  <th>{x}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                <tr
                  className={selected === s[3] ? "selected" : ""}
                  onClick={() => setSelected(s[3])}
                  onDoubleClick={openStock}
                >
                  <td>
                    <Star className={selected === s[3] ? "starred" : ""} />
                  </td>
                  {s.map((v, i) => (
                    <td
                      className={
                        (i === 3 ? "ticker " : "") +
                        (i === 8 ? gradeClass(v) : "") +
                        (String(v).startsWith("-") ? "negative" : "")
                      }
                    >
                      {i === 8 ? <span>{v}</span> : v}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="pagination">
            <span>符合條件檔數：1,856 檔</span>
            <div>
              每頁顯示{" "}
              <button>
                50
                <ChevronDown />
              </button>
              <button>‹</button>
              <button className="current">1</button>
              <button>2</button>
              <button>3</button>
              <b>…</b>
              <button>38</button>
              <button>›</button>
            </div>
          </div>
        </div>
        <RankInsights
          selected={stocks.find((s) => s[3] === selected) || stocks[2]}
        />
      </div>
    </section>
  );
}
function RankInsights({ selected }) {
  return (
    <aside className="insights">
      <Panel title="排名洞察">
        <b className="miniTitle">前 5 大產業分布</b>
        {[
          ["半導體", 39],
          ["電子零組件", 22],
          ["電機機械", 12],
          ["金融保險", 11],
          ["其他電子", 7],
        ].map(([n, v]) => (
          <div className="barRow">
            <span>{n}</span>
            <i>
              <em style={{ width: v * 2 + "%" }} />
            </i>
            <b>{v}%</b>
          </div>
        ))}
      </Panel>
      <Panel title="所選個股六大指標雷達圖">
        <p>
          {selected[3]} {selected[4]}（綜合分數 {selected[7]} / {selected[8]}）
        </p>
        <Radar />
      </Panel>
      <Panel title="財務等級分布">
        <div className="donut">
          <div>
            <b>1,825</b>
            <small>總計</small>
          </div>
        </div>
        <ul className="legend">
          <li>
            <i className="aa" />
            AA　312
          </li>
          <li>
            <i className="a" />
            A　678
          </li>
          <li>
            <i className="bb" />
            BB　421
          </li>
          <li>
            <i className="b" />
            B　198
          </li>
          <li>
            <i className="c" />
            C　123
          </li>
        </ul>
      </Panel>
    </aside>
  );
}
function Panel({ title, children }) {
  return (
    <section className="panel">
      <h3>{title}</h3>
      <div className="panelBody">{children}</div>
    </section>
  );
}
function Radar() {
  return (
    <svg className="radar" viewBox="0 0 240 190">
      <g transform="translate(120 95)">
        {[30, 55, 80].map((r) => (
          <polygon
            points={[0, 1, 2, 3, 4, 5]
              .map(
                (i) =>
                  `${Math.cos(-Math.PI / 2 + (i * Math.PI) / 3) * r},${Math.sin(-Math.PI / 2 + (i * Math.PI) / 3) * r}`,
              )
              .join(" ")}
          />
        ))}
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <line
            x2={Math.cos(-Math.PI / 2 + (i * Math.PI) / 3) * 80}
            y2={Math.sin(-Math.PI / 2 + (i * Math.PI) / 3) * 80}
          />
        ))}
        <polygon
          className="radarValue"
          points="0,-70 57,-33 55,32 0,66 -58,34 -51,-29"
        />
      </g>
    </svg>
  );
}
function StockResearch() {
  return (
    <section className="page stockPage">
      <div className="stockHero">
        <div>
          <h1>2330 台積電</h1>
          <span className="tag blue">上市</span>
          <span className="tag gold">半導體</span>
          <span className="tag">TW6F_GENERAL</span>
        </div>
        <div className="stats">
          {[
            ["綜合得分", "3.67 / 4"],
            ["完整度", "6 / 6"],
            ["模型排名", "12 / 923"],
            ["市場排名", "18 / 923"],
            ["產業排名", "3 / 47"],
            ["模型百分位", "98.7%"],
            ["資料快照", "FINAL"],
            ["資料截止日", "2024/04/30"],
          ].map((x, i) => (
            <div>
              <small>{x[0]}</small>
              <strong className={i === 0 ? "goldText" : ""}>{x[1]}</strong>
            </div>
          ))}
        </div>
      </div>
      <div className="metricStrip">
        {metrics.map((m, i) => (
          <div className={i === 0 ? "active" : ""}>
            <span>{i + 1}</span>
            <b>{m}</b>
            <strong>
              {["AA", "AA", "A", "AA", "A", "AA"][i]}　{[4, 4, 3, 4, 3, 4][i]}
            </strong>
          </div>
        ))}
      </div>
      <div className="tabs">
        <button className="on">指標總覽</button>
        <button>財務趨勢</button>
        <button>Rank 歷史</button>
        <button>資料血緣</button>
      </div>
      <div className="researchGrid">
        <div className="charts">
          <Panel title="營收成長（年成長率 YoY）－近 12 個月">
            <ComboChart />
          </Panel>
          <Panel title="財務趨勢（季）">
            <Bars values={[52, 55, 58, 62, 67, 73, 78, 82, 88, 94, 101, 110]} />
          </Panel>
        </div>
        <DecisionTrace />
      </div>
      <RawTable />
      <Lineage />
    </section>
  );
}
function Bars({ values }) {
  return (
    <div className="bars">
      {values.map((v, i) => (
        <div>
          <i style={{ height: v + "%" }} />
          <small>{i % 2 ? "" : "Q" + (i + 1)}</small>
        </div>
      ))}
    </div>
  );
}
function ComboChart() {
  const max = Math.max(...revenue);
  return (
    <div className="combo">
      <svg viewBox="0 0 720 250" preserveAspectRatio="none">
        <g className="grid">
          {[40, 85, 130, 175, 220].map((y) => (
            <line x1="45" y1={y} x2="700" y2={y} />
          ))}
        </g>
        {revenue.map((v, i) => (
          <rect
            x={55 + i * 53}
            y={220 - (v / max) * 155}
            width="20"
            height={(v / max) * 155}
          />
        ))}
        <polyline
          points={yoy
            .map((v, i) => `${65 + i * 53},${205 - v * 2.35}`)
            .join(" ")}
        />
        {yoy.map((v, i) => (
          <circle cx={65 + i * 53} cy={205 - v * 2.35} r="4" />
        ))}
      </svg>
      <div className="xlabels">
        {months.map((m) => (
          <small>{m}</small>
        ))}
      </div>
    </div>
  );
}
function DecisionTrace() {
  return (
    <Panel title="為何是這個等級：營收成長">
      <dl className="ruleSummary">
        <dt>套用規則</dt>
        <dd>AA-REV-01</dd>
        <dt>等級</dt>
        <dd className="positive">AA（4 / 4）</dd>
        <dt>一句話理由</dt>
        <dd>近 12 個月營收年成長率 59.6%，高於門檻 40%。</dd>
        <dt>計算公式</dt>
        <dd>近 12 個月合計營收 ÷ 前 12 個月合計營收 − 1</dd>
        <dt>品質檢核</dt>
        <dd>● 資料完整　● 近期可得　● 數值合理</dd>
      </dl>
      <div className="trace">
        <h4>決策追蹤（規則評估過程）</h4>
        {[
          ["AA-REV-01", "營收成長率等級判定", "符合"],
          ["A-REV-01", "營收成長率等級判定", "不適用"],
          ["BBB-REV-01", "營收成長率等級判定", "不適用"],
          ["BB-REV-01", "營收成長率等級判定", "不適用"],
        ].map((x, i) => (
          <div>
            <i />
            <b>{x[0]}</b>
            <span>{x[1]}</span>
            <em className={i ? "" : "pass"}>{x[2]}</em>
          </div>
        ))}
      </div>
    </Panel>
  );
}
function RawTable() {
  return (
    <Panel title="原始期間數值（營收，百萬元）">
      <div className="raw">
        <table>
          <tbody>
            <tr>
              <th>期間（月）</th>
              {months.map((x) => (
                <td>{x}</td>
              ))}
              <th>近 12 個月合計</th>
              <th>前 12 個月合計</th>
              <th>成長率 YoY</th>
            </tr>
            <tr>
              <th>營收</th>
              {revenue.map((x) => (
                <td>{x.toLocaleString()}</td>
              ))}
              <td>9,646,437</td>
              <td>6,052,937</td>
              <td className="negative">59.6%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
function Lineage() {
  return (
    <div className="lineage">
      <b>資料來源（血緣）</b>
      {[
        "公開資訊觀測站",
        "財務報表",
        "月營收明細",
        "ETL (Daily)",
        "標準化＆品質檢核",
        "六大財務指標資料庫",
        "Rank 計算引擎 v2.1",
      ].map((x, i) => (
        <React.Fragment key={x}>
          <span>{x}</span>
          {i < 6 && <i />}
        </React.Fragment>
      ))}
    </div>
  );
}
function Quality() {
  const issues = [
    [
      "重大",
      "2330 台積電",
      "2024Q1",
      "營業利益率 OPM",
      "DQ-MISS-001 缺值",
      "TWSE OpenAPI",
      "王小明",
      "未處理",
    ],
    [
      "重大",
      "2888 新光金",
      "2024Q1",
      "權益報酬率 ROE",
      "DQ-ANOM-002 異常值",
      "MOPS",
      "張小華",
      "未處理",
    ],
    [
      "中等",
      "3711 日月光投控",
      "2024Q1",
      "負債比率",
      "DQ-RULE-003 規則不一致",
      "TWSE OpenAPI",
      "陳小強",
      "處理中",
    ],
    [
      "中等",
      "5534 長虹",
      "2024Q1",
      "每股淨值 BVPS",
      "DQ-MISS-004 缺值",
      "TPEx OpenAPI",
      "林小玲",
      "處理中",
    ],
    [
      "低",
      "4105 東洋",
      "2024Q1",
      "現金及約當現金",
      "DQ-FMT-005 格式異常",
      "MOPS",
      "王小明",
      "已處理",
    ],
  ];
  return (
    <section className="page qualityPage">
      <div className="pageTitle">
        <h1>資料品質與重算管理</h1>
        <div>
          <span>目前查看快照　</span>
          <button>
            2024Q1 FINAL v1
            <ChevronDown />
          </button>
          <button className="sync">
            <RefreshCw />
            同步官方資料
          </button>
        </div>
      </div>
      <div className="qualityKpis">
        <div className="fresh">
          <b>來源新鮮度</b>
          <p>
            MOPS　
            <CheckCircle2 />
            最新：2024-05-15 08:45
          </p>
          <p>
            TWSE OpenAPI　
            <CheckCircle2 />
            最新：08:30
          </p>
          <p>
            TPEx OpenAPI　
            <CheckCircle2 />
            最新：08:25
          </p>
        </div>
        {[
          ["宇宙總數", "1,750 檔", "上市 1,024 / 上櫃 726"],
          ["可排名檔數", "1,612 檔", "92.11%"],
          ["臨時 (PROVISIONAL)", "82 檔", "4.69%"],
          ["資料過期 (>3日)", "17 檔", "0.97%"],
          ["未解決重大問題", "6 件", "請儘速處理"],
        ].map((x, i) => (
          <div>
            <small>{x[0]}</small>
            <strong className={i > 2 ? "warn" : ""}>{x[1]}</strong>
            <span>{x[2]}</span>
          </div>
        ))}
      </div>
      <div className="qualityLayout">
        <div>
          <div className="tabs">
            <button>資料新鮮度</button>
            <button className="on">缺值與異常</button>
            <button>工作紀錄</button>
            <button>Taxonomy 映射</button>
            <button>對帳</button>
          </div>
          <div className="miniFilters">
            <button>
              嚴重程度　全部
              <ChevronDown />
            </button>
            <button>
              資料來源　全部
              <ChevronDown />
            </button>
            <button>
              模型／排名　全部
              <ChevronDown />
            </button>
            <button>
              問題狀態　未解決
              <ChevronDown />
            </button>
            <input placeholder="搜尋代碼／名稱／問題代碼" />
          </div>
          <div className="issueTable">
            <table>
              <thead>
                <tr>
                  {[
                    "嚴重程度",
                    "股票代碼／名稱",
                    "期間",
                    "欄位",
                    "問題代碼",
                    "影響模型／排名",
                    "資料來源",
                    "偵測時間",
                    "負責人／狀態",
                    "操作",
                  ].map((x) => (
                    <th>{x}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {issues.map((x, i) => (
                  <React.Fragment>
                    <tr className={i === 4 ? "expanded" : ""}>
                      {x.map((v, j) => (
                        <td
                          className={
                            j === 0
                              ? v === "重大"
                                ? "critical"
                                : v === "中等"
                                  ? "medium"
                                  : "low"
                              : ""
                          }
                        >
                          {j === 0 && <AlertTriangle />}
                          {v}
                        </td>
                      ))}
                      <td>
                        <ChevronDown />
                      </td>
                    </tr>
                    {i === 4 && (
                      <tr className="detailRow">
                        <td colSpan="10">
                          <b>問題詳情</b>
                          <span>
                            來源提供未回傳數值，欄位為空或
                            null。建議檢查公開資訊觀測站原始財報。
                          </span>
                          <b>資料血緣與影響</b>
                          <span>
                            MOPS → 現金及約當現金 → 六大財務指標／產業排名
                          </span>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
          <div className="qualityBottom">
            <Panel title="近期工作紀錄（最近 5 筆）">
              <JobTable />
            </Panel>
            <Panel title="對帳覆蓋率（官方來源 30 檔 QA）">
              <div className="coverage">
                <div className="donut green">
                  <b>93.33%</b>
                  <small>整體覆蓋率</small>
                </div>
                <p>
                  ● 完全一致　28 檔<br />● 部分差異　2 檔<br />● 不一致　0 檔
                </p>
              </div>
            </Panel>
          </div>
        </div>
        <QualityRail />
      </div>
    </section>
  );
}
function JobTable() {
  return (
    <table className="jobs">
      <tbody>
        {[
          "資料擷取與重算",
          "資料擷取與重算",
          "對帳作業",
          "資料擷取",
          "資料擷取",
        ].map((x, i) => (
          <tr>
            <td>{x}</td>
            <td>2024Q1 v1</td>
            <td>{i ? "成功" : "進行中"}</td>
            <td>{i ? "1,750" : "1,190 / 1,750"}</td>
            <td>00:{12 + i * 3}:34</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
function QualityRail() {
  return (
    <aside className="qualityRail">
      <Panel title="待處理佇列">
        <p>
          🔴 重大 <b>6</b>
        </p>
        <p>
          🟠 中等 <b>12</b>
        </p>
        <p>
          🔵 低 <b>24</b>
        </p>
      </Panel>
      <Panel title="目前資料擷取／重算作業">
        <dl>
          <dt>來源</dt>
          <dd>MOPS / TWSE / TPEx</dd>
          <dt>進度</dt>
          <dd>
            <progress value="68" max="100" /> 68%
          </dd>
          <dt>狀態</dt>
          <dd className="positive">● 執行中</dd>
          <dt>已處理</dt>
          <dd>1,190 / 1,750 檔</dd>
        </dl>
        <button className="primary full">重試作業</button>
      </Panel>
      <Panel title="建立新快照">
        <p>① 選擇來源資料　② 設定與重算　③ 發布設定</p>
        <label>
          <input type="radio" name="s" /> PROVISIONAL（臨時發布）
        </label>
        <label>
          <input type="radio" name="s" defaultChecked /> FINAL（正式發布）
        </label>
        <button className="primary full">建立新快照</button>
        <div className="notice">
          <AlertTriangle />
          已發布之 FINAL 快照為不可變更。
        </div>
      </Panel>
    </aside>
  );
}
function Galaxy() {
  return (
    <section className="page visualPage">
      <div className="pageTitle">
        <div>
          <h1>星系關聯圖</h1>
          <p>產業群聚、財務相似性與資料依存關係；關聯不代表因果。</p>
        </div>
        <div>
          <button>
            全部產業
            <ChevronDown />
          </button>
          <button>
            關聯門檻 0.35
            <ChevronDown />
          </button>
        </div>
      </div>
      <div className="galaxyCanvas">
        <svg viewBox="0 0 1200 700">
          {Array.from({ length: 70 }, (_, i) => {
            const a = i * 2.399,
              r = 30 + (i % 18) * 19,
              cx = i < 24 ? 280 : i < 48 ? 700 : 980,
              cy = i < 24 ? 260 : i < 48 ? 400 : 210;
            return (
              <circle
                cx={cx + Math.cos(a) * r}
                cy={cy + Math.sin(a) * r}
                r={3 + (i % 7)}
                className={"node n" + (i % 4)}
              />
            );
          })}
          <g className="clusterLabels">
            <text x="190" y="80">
              半導體星系
            </text>
            <text x="625" y="155">
              電子零組件
            </text>
            <text x="900" y="70">
              金融保險
            </text>
          </g>
        </svg>
        <div className="canvasLegend">
          節點大小：模型百分位　光環：完整度　連線：標準化關聯強度
        </div>
      </div>
    </section>
  );
}
function Heatmap() {
  const cells = Array.from({ length: 96 }, (_, i) => ({
    x: i % 16,
    y: Math.floor(i / 16),
    h: 20 + ((i * 37) % 120),
    v: 70 + ((i * 17) % 30),
  }));
  return (
    <section className="page visualPage">
      <div className="pageTitle">
        <div>
          <h1>3D 排名熱力圖</h1>
          <p>產業、綜合分數、模型百分位與完整度的立體分布。</p>
        </div>
        <div>
          <button>
            透視檢視
            <ChevronDown />
          </button>
          <button>展平為 2D</button>
        </div>
      </div>
      <div className="heatCanvas">
        <div className="heatScene">
          {cells.map((c) => (
            <i
              style={{ "--x": c.x, "--y": c.y, "--h": c.h, "--v": c.v }}
              title={`百分位 ${c.v}`}
            />
          ))}
        </div>
        <div className="axis x">產業 →</div>
        <div className="axis y">綜合分數 →</div>
        <div className="canvasLegend">
          Z：模型內百分位　顏色：財務等級　柱頂：資料完整度
        </div>
      </div>
    </section>
  );
}
function Coming({ title }) {
  return (
    <section className="page coming">
      <GitBranch />
      <h1>{title}</h1>
      <p>此模組將沿用相同資料快照、品質狀態與可追溯規則。</p>
    </section>
  );
}
createRoot(document.getElementById("root")).render(<App />);
