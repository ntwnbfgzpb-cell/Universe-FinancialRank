from __future__ import annotations

import csv
import json
import math
import random
import queue
import sys
import threading
import tempfile
from datetime import date
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk
try:
    from .core import LocalRepository, RankingEngine
    from .core.ingest import ImportValidationError, OfficialImportPipeline
    from .core.providers import TwseOpenApiRawAdapter
    from .core.bronze import normalize_twse_bronze
    from .backup_restore import create_backup
    from .auto_update import run_update
except ImportError:
    from core import LocalRepository, RankingEngine
    from core.ingest import ImportValidationError, OfficialImportPipeline
    from core.providers import TwseOpenApiRawAdapter
    from core.bronze import normalize_twse_bronze
    from backup_restore import create_backup
    from auto_update import run_update

APP_DIR = Path(__file__).resolve().parent
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", APP_DIR.parent))
ASSET_DIR = RESOURCE_ROOT / "project-assets" / "cosmic-finance"
DATA_DIR = (Path(tempfile.gettempdir()) / "six_financial_rank_self_test"
            if "--self-test" in sys.argv else Path.home() / ".six_financial_rank")
DATA_DIR.mkdir(parents=True, exist_ok=True)
PREFS_FILE = DATA_DIR / "window_state.json"

NAVY = "#102A43"
NAVY_DARK = "#06182C"
GOLD = "#B89B5E"
PAPER = "#FBFAF7"
INK = "#142637"
MUTED = "#66788A"
LINE = "#DCE2E8"
BLUE = "#2878B8"
GREEN = "#16805B"
AMBER = "#B87919"
RED = "#B64545"

METRICS = ["營收成長", "營業利益率", "淨利成長", "EPS", "存貨週轉", "自由現金流"]
STOCKS = [
    (1, "1/45", 99.7, "2330", "台積電", "上市", "半導體", 3.83, 100, ("AA","AA","A","AA","A","AA"), "FINAL"),
    (2, "1/28", 98.9, "2454", "聯發科", "上市", "半導體", 3.67, 100, ("AA","AA","AA","AA","BB","A"), "FINAL"),
    (3, "1/32", 97.1, "2308", "台達電", "上市", "電子零組件", 3.50, 100, ("A","AA","AA","AA","A","A"), "FINAL"),
    (4, "2/45", 95.4, "2317", "鴻海", "上市", "電子零組件", 3.17, 100, ("A","A","AA","A","BB","A"), "FINAL"),
    (5, "1/15", 93.8, "3711", "日月光投控", "上市", "半導體", 3.00, 100, ("A","A","A","A","BB","A"), "FINAL"),
    (6, "1/18", 92.2, "2882", "國泰金", "上市", "金融保險", 3.00, 100, ("AA","A","A","A","N/A","N/A"), "FINAL"),
    (7, "2/18", 90.6, "2891", "中信金", "上市", "金融保險", 2.75, 100, ("A","A","A","A","N/A","N/A"), "FINAL"),
    (8, "2/15", 88.9, "1519", "華城", "上市", "電機機械", 2.83, 83, ("AA","A","A","BB","N/A","A"), "PROVISIONAL"),
    (9, "1/12", 87.4, "2603", "長榮", "上市", "航運", 2.67, 100, ("BB","AA","A","AA","BB","BB"), "FINAL"),
    (10, "1/31", 85.2, "6488", "環球晶", "上櫃", "半導體", 2.50, 100, ("BB","A","A","A","BB","A"), "FINAL"),
    (11, "3/32", 83.7, "3034", "聯詠", "上市", "半導體", 2.33, 100, ("A","A","BB","AA","B","BB"), "FINAL"),
    (12, "4/32", 81.1, "2379", "瑞昱", "上市", "半導體", 2.17, 100, ("A","A","B","AA","BB","C"), "FINAL"),
]

GRADE_COLORS = {
    "AA": ("#EAF7EF", "#126842"),
    "A": ("#F1F8F4", "#2C7359"),
    "BB": ("#EEF6FB", "#2C6F9D"),
    "B": ("#FFF6E5", "#A86C12"),
    "C": ("#FFF0F0", "#AA4646"),
    "N/A": ("#F1F3F4", "#76818A"),
}


class RankDesktop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("六大財務指標 Rank｜臺股基本面研究")
        self.minsize(1080, 680)
        self.configure(bg=PAPER)
        self.repository = LocalRepository(DATA_DIR / "rank_local.db")
        self.engine = RankingEngine()
        self.stocks = list(STOCKS)
        self.data_source = "DEMO FIXTURE"
        self.active_snapshot = None
        self._load_latest_snapshot()
        self._restore_geometry()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.option_add("*Font", ("Microsoft JhengHei", 10))
        self.filtered = list(self.stocks)
        self.current_view = "排行榜"
        self.sort_column = "模型排名"
        self.sort_reverse = False
        self.sidebar_image = None
        self._setup_style()
        self._build_shell()
        self.show_ranking()

    def _setup_style(self):
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Treeview", background="white", fieldbackground="white", foreground=INK,
                        rowheight=34, bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
        style.configure("Treeview.Heading", background="#F4F6F8", foreground="#4F6273",
                        font=("Microsoft JhengHei", 9, "bold"), padding=7)
        style.map("Treeview", background=[("selected", "#FFF5DE")], foreground=[("selected", INK)])
        style.configure("TCombobox", padding=6)

    def _restore_geometry(self):
        geometry = "1460x900"
        try:
            prefs = json.loads(PREFS_FILE.read_text(encoding="utf-8"))
            geometry = prefs.get("geometry", geometry)
        except (OSError, ValueError):
            pass
        self.geometry(geometry)

    def _close(self):
        try:
            PREFS_FILE.write_text(json.dumps({"geometry": self.geometry()}, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
        self.repository.close()
        self.destroy()

    def _build_shell(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = tk.Canvas(self, width=225, bg=NAVY_DARK, highlightthickness=0)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.bind("<Configure>", self._paint_sidebar)
        self.nav_buttons = {}
        tk.Label(self.sidebar, text="✦  六大財務指標 Rank", bg=NAVY_DARK, fg="#F1D187",
                 font=("Microsoft JhengHei", 15, "bold")).place(x=18, y=24)
        tk.Label(self.sidebar, text="臺股基本面研究工具", bg=NAVY_DARK, fg="#AEBECD",
                 font=("Microsoft JhengHei", 9)).place(x=44, y=52)
        items = [
            ("排行榜", self.show_ranking),
            ("個股研究", self.show_stock_default),
            ("星系關聯圖", self.show_galaxy),
            ("3D 排名熱力圖", self.show_heatmap),
            ("資料品質", self.show_quality),
        ]
        for i, (name, command) in enumerate(items):
            button = tk.Button(self.sidebar, text=name, anchor="w", padx=22, relief="flat",
                               borderwidth=0, bg=NAVY_DARK, fg="#DCE7F1",
                               activebackground="#173653", activeforeground="white",
                               font=("Microsoft JhengHei", 11), command=command)
            button.place(x=8, y=92 + i * 48, width=209, height=40)
            self.nav_buttons[name] = button
        tk.Label(self.sidebar, text="TW-RANK-SPEC v1.2\n研究資訊工具｜不提供交易訊號",
                 justify="left", bg=NAVY_DARK, fg="#8195A7",
                 font=("Microsoft JhengHei", 8)).place(x=18, rely=1.0, y=-58)

        right = tk.Frame(self, bg=PAPER)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)
        top = tk.Frame(right, bg="white", height=64, highlightbackground=LINE, highlightthickness=1)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_propagate(False)
        tk.Label(top, text="資料快照", bg="white", fg=MUTED).pack(side="left", padx=(26, 8))
        self.snapshot_label = tk.Label(top, text="尚無本機快照", bg="white", fg=INK,
                 font=("Microsoft JhengHei", 10, "bold"))
        self.snapshot_label.pack(side="left")
        self.demo_label = tk.Label(top, text="示範資料", bg="#FFF6DA", fg="#78571C",
                                   padx=8, pady=4, font=("Microsoft JhengHei", 9))
        self.demo_label.pack(side="right", padx=(8, 24))
        tk.Button(top, text="匯出 CSV", command=self.export_csv, relief="solid", borderwidth=1,
                  bg="white", fg=INK, padx=12).pack(side="right")
        tk.Button(top, text="切換快照", command=self.choose_snapshot, relief="solid", borderwidth=1,
                  bg="white", fg=INK, padx=12).pack(side="right", padx=(8,0))
        tk.Button(top, text="建立本機快照", command=self.rebuild_demo_snapshot, relief="solid",
                  borderwidth=1, bg="white", fg=INK, padx=12).pack(side="right", padx=8)
        tk.Button(top, text="匯入官方 CSV", command=self.import_official_csv, relief="solid",
                  borderwidth=1, bg="white", fg=INK, padx=12).pack(side="right")
        tk.Button(top, text="同步官方原始資料", command=self.sync_official_raw, relief="solid",
                  borderwidth=1, bg="white", fg=INK, padx=12).pack(side="right", padx=(0,8))
        self.content = tk.Frame(right, bg=PAPER)
        self.content.grid(row=1, column=0, sticky="nsew")
        self._refresh_source_labels()

    def _load_latest_snapshot(self, snapshot_id=None):
        snapshot = self.repository.snapshot(snapshot_id) if snapshot_id else self.repository.latest_snapshot(status=None)
        if snapshot is None:
            return False
        rows = self.repository.desktop_rankings(snapshot["snapshot_id"])
        if not rows:
            return False
        self.stocks = rows
        self.active_snapshot = snapshot
        cutoffs = json.loads(snapshot["source_cutoffs_json"])
        self.data_source = "DEMO FIXTURE" if cutoffs.get("official") is False else "離線匯入資料"
        return True

    def _refresh_source_labels(self):
        if not hasattr(self, "snapshot_label"):
            return
        if self.active_snapshot:
            self.snapshot_label.configure(
                text=f"{self.active_snapshot['as_of_date']} {self.active_snapshot['status']}"
            )
        else:
            self.snapshot_label.configure(text="尚無本機快照")
        is_demo = self.data_source == "DEMO FIXTURE"
        self.demo_label.configure(
            text="示範資料" if is_demo else "離線匯入｜待來源核驗",
            bg="#FFF6DA" if is_demo else "#EAF4FB",
            fg="#78571C" if is_demo else "#245F87",
        )

    def choose_snapshot(self):
        snapshots = self.repository.snapshots()
        if not snapshots:
            messagebox.showinfo("切換快照", "目前沒有本機快照。", parent=self)
            return
        dialog = tk.Toplevel(self)
        dialog.title("選擇不可變快照")
        dialog.geometry("820x430")
        frame = tk.Frame(dialog, bg=PAPER, padx=18, pady=16)
        frame.pack(fill="both", expand=True)
        columns = ("日期", "狀態", "規則版本", "建立時間", "Checksum")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for column, width in zip(columns, (100,100,190,190,190)):
            tree.heading(column, text=column)
            tree.column(column, width=width, anchor="center")
        for snapshot in snapshots:
            tree.insert("", "end", iid=snapshot["snapshot_id"], values=(snapshot["as_of_date"],
                snapshot["status"], snapshot["rule_version"], snapshot["created_at"][:19],
                snapshot["checksum"][:20] + "…"))
        tree.pack(fill="both", expand=True)

        def activate(_event=None):
            selected = tree.selection()
            if not selected:
                return
            if not self._load_latest_snapshot(selected[0]):
                messagebox.showwarning("無排名資料", "此快照沒有可顯示的排名。", parent=dialog)
                return
            self.filtered = list(self.stocks)
            self._refresh_source_labels()
            dialog.destroy()
            self.show_ranking()

        tree.bind("<Double-1>", activate)
        tk.Button(frame, text="載入選取快照", command=activate, bg=NAVY, fg="white",
                  relief="flat", padx=18, pady=7).pack(anchor="e", pady=(10,0))

    def _paint_sidebar(self, _event=None):
        path = ASSET_DIR / "bg-cosmic-sidebar-navy.png"
        if not path.exists():
            return
        try:
            image = Image.open(path).convert("RGB")
            image = image.resize((225, max(self.sidebar.winfo_height(), 680)), Image.Resampling.LANCZOS)
            self.sidebar_image = ImageTk.PhotoImage(image)
            self.sidebar.create_image(0, 0, image=self.sidebar_image, anchor="nw", tags="background")
            self.sidebar.tag_lower("background")
        except OSError:
            pass

    def _activate(self, name):
        self.current_view = name
        for label, button in self.nav_buttons.items():
            button.configure(bg="#173653" if label == name else NAVY_DARK,
                             fg="white" if label == name else "#DCE7F1")
        for child in self.content.winfo_children():
            child.destroy()

    def _page(self, title, subtitle):
        page = tk.Frame(self.content, bg=PAPER, padx=26, pady=22)
        page.pack(fill="both", expand=True)
        tk.Label(page, text=title, bg=PAPER, fg=INK,
                 font=("Microsoft JhengHei", 22, "bold")).pack(anchor="w")
        tk.Label(page, text=subtitle, bg=PAPER, fg=MUTED,
                 font=("Microsoft JhengHei", 10)).pack(anchor="w", pady=(4, 16))
        return page

    def show_ranking(self):
        self._activate("排行榜")
        page = self._page("臺股基本面排行榜", "六項財務評等、模型百分位與資料完整度；預設顯示 FINAL 快照。")
        filters = tk.Frame(page, bg="white", padx=14, pady=13, highlightbackground=LINE, highlightthickness=1)
        filters.pack(fill="x", pady=(0, 14))
        self.query = tk.StringVar()
        self.market = tk.StringVar(value="全部")
        self.industry = tk.StringVar(value="全部")
        active_status = self.active_snapshot["status"] if self.active_snapshot else "FINAL"
        self.snapshot = tk.StringVar(value=active_status)
        industries = sorted({stock[6] for stock in self.stocks})
        entries = [
            ("代號／名稱", tk.Entry(filters, textvariable=self.query, relief="solid", borderwidth=1)),
            ("市場", ttk.Combobox(filters, textvariable=self.market, state="readonly",
                                values=["全部", "上市", "上櫃"])),
            ("產業", ttk.Combobox(filters, textvariable=self.industry, state="readonly",
                                values=["全部"] + industries)),
            ("快照狀態", ttk.Combobox(filters, textvariable=self.snapshot, state="readonly",
                                  values=["FINAL", "全部", "PROVISIONAL"])),
        ]
        for col, (label, widget) in enumerate(entries):
            filters.grid_columnconfigure(col, weight=2 if col == 0 else 1)
            tk.Label(filters, text=label, bg="white", fg=INK,
                     font=("Microsoft JhengHei", 9, "bold")).grid(row=0, column=col, sticky="w", padx=5)
            widget.grid(row=1, column=col, sticky="ew", padx=5, pady=(5, 0), ipady=5)
        tk.Button(filters, text="套用條件", bg=NAVY, fg="white", relief="flat",
                  command=self.apply_filters, padx=14).grid(row=1, column=4, padx=(12, 4), sticky="ns")

        table_frame = tk.Frame(page, bg="white", highlightbackground=LINE, highlightthickness=1)
        table_frame.pack(fill="both", expand=True)
        columns = ["模型排名","同業排名","百分位","代號","名稱","市場","產業","綜合分數","完整度"] + METRICS + ["狀態"]
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        widths = [75,75,70,65,110,60,105,80,70] + [78]*6 + [95]
        for name, width in zip(columns, widths):
            self.tree.heading(name, text=name, command=lambda c=name: self.sort_tree(c))
            self.tree.column(name, width=width, minwidth=55, anchor="center")
        self.tree.column("名稱", anchor="w")
        self.tree.bind("<Double-1>", self.open_selected_stock)
        self.tree.bind("<Return>", self.open_selected_stock)
        self.count_label = tk.Label(page, bg=PAPER, fg=MUTED)
        self.count_label.pack(anchor="w", pady=(8, 0))
        self.apply_filters()

    def apply_filters(self):
        query = self.query.get().strip()
        market = self.market.get()
        industry = self.industry.get()
        snapshot = self.snapshot.get()
        self.filtered = [
            stock for stock in self.stocks
            if (not query or query in stock[3] or query in stock[4])
            and (market == "全部" or stock[5] == market)
            and (industry == "全部" or stock[6] == industry)
            and (snapshot == "全部" or stock[10] == snapshot)
        ]
        self._populate_tree()

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for stock in self.filtered:
            values = stock[:9] + stock[9] + (stock[10],)
            tag = "provisional" if stock[10] == "PROVISIONAL" else "final"
            self.tree.insert("", "end", iid=stock[3], values=values, tags=(tag,))
        self.tree.tag_configure("provisional", foreground=AMBER)
        self.tree.tag_configure("final", foreground=INK)
        source = "示範母體" if self.data_source == "DEMO FIXTURE" else "本機不可變快照"
        self.count_label.configure(text=f"符合條件：{len(self.filtered)} 檔（{source}）｜跨模型僅比較模型內百分位")

    def sort_tree(self, column):
        columns = list(self.tree["columns"])
        index = columns.index(column)
        reverse = self.sort_reverse if column == self.sort_column else False
        self.filtered.sort(key=lambda row: row[:9] + row[9] + (row[10],), reverse=False)
        self.filtered.sort(key=lambda row: (row[:9] + row[9] + (row[10],))[index], reverse=reverse)
        self.sort_column = column
        self.sort_reverse = not reverse
        self._populate_tree()

    def open_selected_stock(self, _event=None):
        selected = self.tree.selection()
        if selected:
            self.show_stock(next(s for s in self.stocks if s[3] == selected[0]), new_window=True)

    def show_stock_default(self):
        if self.stocks:
            self.show_stock(self.stocks[0], new_window=False)

    def show_stock(self, stock, new_window=False):
        if new_window:
            window = tk.Toplevel(self)
            window.title(f"{stock[3]} {stock[4]}｜個股研究")
            window.geometry("1060x720")
            container = tk.Frame(window, bg=PAPER, padx=22, pady=20)
            container.pack(fill="both", expand=True)
        else:
            self._activate("個股研究")
            container = self._page(f"{stock[3]} {stock[4]}", "個股評等、財務趨勢與可追溯決策軌跡。")
        header = tk.Frame(container, bg="white", padx=16, pady=15, highlightbackground=LINE, highlightthickness=1)
        header.pack(fill="x")
        tk.Label(header, text=f"{stock[3]} {stock[4]}", bg="white", fg=INK,
                 font=("Microsoft JhengHei", 20, "bold")).grid(row=0, column=0, sticky="w")
        model_code = "TW6F_GENERAL"
        metric_rows = []
        if self.active_snapshot:
            metric_rows = self.repository.metric_results(self.active_snapshot["snapshot_id"], stock[3])
            ranking = next((r for r in self.repository.rankings(self.active_snapshot["snapshot_id"])
                            if r["symbol"] == stock[3]), None)
            if ranking:
                model_code = ranking["model_code"]
        tk.Label(header, text=f"{stock[5]}｜{stock[6]}｜{model_code}", bg="white", fg=MUTED).grid(row=1, column=0, sticky="w")
        stats = [("綜合分數", f"{stock[7]:.2f}"), ("完整度", f"{stock[8]}%"),
                 ("模型排名", str(stock[0])), ("模型百分位", f"{stock[2]}%")]
        for i, (label, value) in enumerate(stats, start=1):
            header.grid_columnconfigure(i, weight=1)
            tk.Label(header, text=label, bg="white", fg=MUTED).grid(row=0, column=i)
            tk.Label(header, text=value, bg="white", fg=INK,
                     font=("Microsoft JhengHei", 16, "bold")).grid(row=1, column=i)
        tk.Button(header, text="排名歷史", command=lambda: self.show_rank_history(stock),
                  bg="white", fg=INK, relief="solid", borderwidth=1).grid(row=2, column=1, pady=(10,0), padx=3)
        tk.Button(header, text="來源血緣", command=lambda: self.show_lineage(stock),
                  bg="white", fg=INK, relief="solid", borderwidth=1).grid(row=2, column=2, pady=(10,0), padx=3)
        rail = tk.Frame(container, bg="white", highlightbackground=LINE, highlightthickness=1)
        rail.pack(fill="x", pady=12)
        for i, (metric, grade) in enumerate(zip(METRICS, stock[9])):
            rail.grid_columnconfigure(i, weight=1)
            bg, fg = GRADE_COLORS[grade]
            box = tk.Frame(rail, bg="white", padx=8, pady=10)
            box.grid(row=0, column=i, sticky="nsew")
            tk.Label(box, text=metric, bg="white", fg=MUTED).pack()
            tk.Label(box, text=grade, bg=bg, fg=fg, padx=10, pady=3,
                     font=("Microsoft JhengHei", 11, "bold")).pack(pady=(6, 0))
        body = tk.PanedWindow(container, orient="horizontal", sashwidth=5, bg=LINE)
        body.pack(fill="both", expand=True)
        chart = tk.Canvas(body, bg="white", highlightthickness=0)
        trace = tk.Frame(body, bg="white", padx=18, pady=16)
        body.add(chart, stretch="always", minsize=520)
        body.add(trace, stretch="always", minsize=320)
        revenue_values = []
        if self.active_snapshot:
            for fact in self.repository.financial_facts(stock[3], self.active_snapshot["as_of_date"]):
                if fact["metric_code"] == "REVENUE_YOY":
                    try:
                        revenue_values.append(float(fact["value_text"]))
                    except ValueError:
                        pass
        chart.bind("<Configure>", lambda e: self._draw_bar_chart(chart, revenue_values))
        tk.Label(trace, text="為何是這個等級", bg="white", fg=INK,
                 font=("Microsoft JhengHei", 15, "bold")).pack(anchor="w")
        trace_items = [(f"{row['rule_id']}｜{row['grade']}", row["reason_text"])
                       for row in metric_rows[:6]]
        if not trace_items:
            trace_items = [
                ("示範決策軌跡", "尚未匯入可追溯資料；此畫面只驗證介面與操作流程。"),
                ("資料品質", "請匯入帶公告日與可用日的 CSV 後建立快照。"),
            ]
        for title, detail in trace_items:
            frame = tk.Frame(trace, bg="white", highlightbackground=LINE, highlightthickness=1, padx=11, pady=9)
            frame.pack(fill="x", pady=5)
            tk.Label(frame, text=title, bg="white", fg=INK,
                     font=("Microsoft JhengHei", 10, "bold")).pack(anchor="w")
            tk.Label(frame, text=detail, bg="white", fg=MUTED, wraplength=340,
                     justify="left").pack(anchor="w", pady=(4, 0))
        footer = ("目前為示範內容，不能視為官方排名。" if not metric_rows else
                  "決策理由來自本機不可變快照；離線匯入來源仍需人工核驗。")
        tk.Label(trace, text=footer,
                 bg="white", fg=AMBER, wraplength=340, justify="left").pack(anchor="w", pady=12)

    def show_rank_history(self, stock):
        window = tk.Toplevel(self)
        window.title(f"{stock[3]} {stock[4]}｜排名歷史")
        window.geometry("850x500")
        frame = tk.Frame(window, bg=PAPER, padx=18, pady=16)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="不可變快照排名歷史", bg=PAPER, fg=INK,
                 font=("Microsoft JhengHei", 17, "bold")).pack(anchor="w", pady=(0,10))
        columns = ("資料日","狀態","模型","分數","模型排名","市場排名","同業排名","百分位")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for column, width in zip(columns, (90,90,150,80,80,80,80,80)):
            tree.heading(column, text=column); tree.column(column, width=width, anchor="center")
        for row in self.repository.rank_history(stock[3]):
            tree.insert("", "end", values=(row["as_of_date"],row["status"],row["model_code"],
                row["overall_score"],row["rank_model"],row["rank_market"],row["rank_industry"],
                f"{float(row['model_percentile']):.1f}%"))
        tree.pack(fill="both", expand=True)

    def show_lineage(self, stock):
        window = tk.Toplevel(self)
        window.title(f"{stock[3]} {stock[4]}｜來源血緣")
        window.geometry("1050x620")
        frame = tk.Frame(window, bg=PAPER, padx=18, pady=16)
        frame.pack(fill="both", expand=True)
        if not self.active_snapshot:
            tk.Label(frame, text="尚未載入快照", bg=PAPER, fg=AMBER).pack()
            return
        tk.Label(frame, text=f"Snapshot {self.active_snapshot['snapshot_id']}", bg=PAPER, fg=INK,
                 font=("Microsoft JhengHei", 13, "bold")).pack(anchor="w")
        tk.Label(frame, text=f"Checksum {self.active_snapshot['checksum']}", bg=PAPER, fg=MUTED).pack(anchor="w", pady=(2,10))
        notebook = ttk.Notebook(frame); notebook.pack(fill="both", expand=True)
        metrics_tab = tk.Frame(notebook, bg="white"); facts_tab = tk.Frame(notebook, bg="white")
        notebook.add(metrics_tab, text="評等與規則"); notebook.add(facts_tab, text="來源財務事實")
        metric_columns = ("指標","等級","分數","規則","理由","品質旗標")
        metric_tree = ttk.Treeview(metrics_tab, columns=metric_columns, show="headings")
        for column, width in zip(metric_columns, (150,60,60,130,360,180)):
            metric_tree.heading(column,text=column); metric_tree.column(column,width=width,anchor="w")
        for row in self.repository.metric_results(self.active_snapshot["snapshot_id"], stock[3]):
            metric_tree.insert("","end",values=(row["metric_code"],row["grade"],row["score"] or "—",
                row["rule_id"],row["reason_text"],row["quality_flags_json"]))
        metric_tree.pack(fill="both",expand=True)
        fact_columns = ("指標","期別","原始值","單位","公告日","可用日","來源","版本","SHA-256")
        fact_tree = ttk.Treeview(facts_tab, columns=fact_columns, show="headings")
        for column,width in zip(fact_columns,(145,90,110,80,90,90,120,80,170)):
            fact_tree.heading(column,text=column); fact_tree.column(column,width=width,anchor="w")
        for row in self.repository.financial_facts(stock[3], self.active_snapshot["as_of_date"]):
            fact_tree.insert("","end",values=(row["metric_code"],row["period"],row["value_text"],row["unit"],
                row["published_at"],row["available_at"],row["provider"],row["version"],row["sha256"][:20]+"…"))
        fact_tree.pack(fill="both",expand=True)

    def _draw_bar_chart(self, canvas, values=None):
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        canvas.create_text(22, 22, text="近 12 個月營收年增趨勢", anchor="w",
                           fill=INK, font=("Microsoft JhengHei", 14, "bold"))
        values = values or [42,55,49,65,58,72,69,81,75,88,93,100]
        left, right, top, bottom = 45, width - 25, 65, height - 38
        canvas.create_line(left, top, left, bottom, right, bottom, fill="#AAB5BF")
        bar_width = max(10, (right-left) / len(values) * 0.58)
        gap = (right-left) / len(values)
        for i, value in enumerate(values):
            x = left + gap * (i + .5)
            scale = max(max(values), 1)
            y = bottom - (bottom-top) * max(value, 0) / scale
            canvas.create_rectangle(x-bar_width/2, y, x+bar_width/2, bottom,
                                    fill="#C9A45A", outline="")
            canvas.create_text(x, bottom+12, text=str(i+1), fill=MUTED, font=("Arial", 8))

    def show_galaxy(self):
        self._activate("星系關聯圖")
        page = self._page("星系關聯圖", "產業群聚與財務指標的進階探索；關聯不代表因果。")
        canvas = tk.Canvas(page, bg=NAVY_DARK, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.bind("<Configure>", lambda e: self._draw_galaxy(canvas))

    def _draw_galaxy(self, canvas):
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        random.seed(12)
        for _ in range(90):
            x, y = random.randrange(max(width,1)), random.randrange(max(height,1))
            canvas.create_oval(x, y, x+1, y+1, fill="#55748C", outline="")
        industries = sorted({stock[6] for stock in self.stocks})[:6]
        palette = ["#D5AD58", "#68C6CF", "#6FAEE0", "#8BD0DA", "#D98A6A", "#A995D6"]
        clusters = [(name, .27 + (i % 3) * .25, .30 + (i // 3) * .43, palette[i])
                    for i, name in enumerate(industries)]
        for label, rx, ry, color in clusters:
            cx, cy = width*rx, height*ry
            canvas.create_text(cx, cy-90, text=label, fill=color,
                               font=("Microsoft JhengHei", 14, "bold"))
            members = [stock for stock in self.stocks if stock[6] == label]
            points = []
            for i, stock in enumerate(members[:18]):
                angle = i * 2.36
                radius = 25 + (i % 5) * 13
                points.append((cx+math.cos(angle)*radius, cy+math.sin(angle)*radius, stock))
            for i, point in enumerate(points):
                if i:
                    canvas.create_line(points[i-1][0], points[i-1][1], point[0], point[1], fill=color, width=1)
                size = 3 + int(point[2][2] / 25)
                canvas.create_oval(point[0]-size, point[1]-size, point[0]+size, point[1]+size,
                                   fill=color, outline="")
                canvas.create_text(point[0]+7, point[1], text=point[2][3], anchor="w",
                                   fill="#D8E4ED", font=("Microsoft JhengHei", 7))
        canvas.create_text(18, height-18, anchor="sw",
                           text="節點大小：模型百分位　光環：完整度　連線：標準化關聯強度",
                           fill="#D8E4ED", font=("Microsoft JhengHei", 9))

    def show_heatmap(self):
        self._activate("3D 排名熱力圖")
        page = self._page("3D 排名熱力圖", "產業、模型百分位、綜合分數與完整度的立體分布。")
        canvas = tk.Canvas(page, bg=NAVY_DARK, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.bind("<Configure>", lambda e: self._draw_heatmap(canvas))

    def _draw_heatmap(self, canvas):
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        base = height * .84
        for level in range(7):
            y = base-level*65
            canvas.create_line(85, y, width-45, y, fill="#405F78")
        for col in range(10):
            x = 100+col*(width-180)/9
            canvas.create_line(x, base, x+130, 95, fill="#314E65")
        population = self.stocks * max(1, 72 // max(len(self.stocks), 1))
        for i, stock in enumerate(population):
            x = 115 + (i % 14) * max(48, (width-220)/14)
            y = base - (i//14)*24
            bar_height = 35 + stock[7]*72
            color = "#D7B15E" if stock[7] > 3 else "#61A6D7"
            canvas.create_line(x, y, x, y-bar_height, fill=color, width=3)
            canvas.create_oval(x-4, y-bar_height-4, x+4, y-bar_height+4, fill=color, outline="")
        canvas.create_text(18, height-18, anchor="sw",
                           text="X：產業分類　Y：綜合分數　Z：模型內百分位　節點：完整度",
                           fill="#D8E4ED", font=("Microsoft JhengHei", 9))

    def show_quality(self):
        self._activate("資料品質")
        page = self._page("資料品質與重算管理", "官方來源新鮮度、缺值、異常與工作狀態。")
        actions = tk.Frame(page, bg=PAPER)
        actions.pack(fill="x", pady=(0,10))
        tk.Button(actions, text="同步官方原始資料", command=self.sync_official_raw,
                  bg=NAVY, fg="white", relief="flat", padx=14, pady=6).pack(side="left")
        tk.Button(actions, text="一鍵自動更新暫定榜", command=self.run_auto_update,
                  bg=GOLD, fg=NAVY_DARK, relief="flat", padx=14, pady=6).pack(side="left", padx=(8,0))
        tk.Button(actions, text="備份本機資料庫", command=self.backup_database,
                  bg="white", fg=INK, relief="solid", borderwidth=1, padx=14, pady=6).pack(side="left", padx=8)
        cards = tk.Frame(page, bg=PAPER)
        cards.pack(fill="x", pady=(0, 14))
        summary = self.repository.quality_summary()
        for i, (label, value) in enumerate([
            ("母體檔數", str(summary["universe"])), ("可排名檔數", str(summary["ranked"])),
            ("暫定快照", str(summary["provisional"])), ("重大未解問題", str(summary["critical"])),
        ]):
            cards.grid_columnconfigure(i, weight=1)
            frame = tk.Frame(cards, bg="white", padx=16, pady=14,
                             highlightbackground=LINE, highlightthickness=1)
            frame.grid(row=0, column=i, sticky="ew", padx=(0 if i==0 else 5, 0))
            tk.Label(frame, text=label, bg="white", fg=MUTED).pack(anchor="w")
            tk.Label(frame, text=value, bg="white", fg=INK,
                     font=("Microsoft JhengHei", 19, "bold")).pack(anchor="w", pady=(5,0))
        columns = ("嚴重度","股票","期別","問題","來源","狀態")
        tree = ttk.Treeview(page, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=130 if col != "問題" else 260, anchor="w")
        severity_labels = {"CRITICAL":"重大", "WARNING":"中等", "INFO":"低"}
        for issue in self.repository.quality_issues():
            stock_label = f"{issue['symbol'] or '—'} {issue['name'] or ''}".strip()
            tree.insert("", "end", values=(severity_labels.get(issue["severity"], issue["severity"]),
                stock_label, issue["period"] or "—", issue["details"], issue["provider"], "待處理"))
        if not tree.get_children():
            tree.insert("", "end", values=("—","—","—","目前沒有未解資料品質問題","本機資料庫","正常"))
        tree.pack(fill="both", expand=True)

    def backup_database(self):
        directory = filedialog.askdirectory(title="選擇備份資料夾")
        if not directory:
            return
        try:
            backup, manifest = create_backup(self.repository.path, directory)
        except (OSError, ValueError) as error:
            messagebox.showerror("備份失敗", str(error), parent=self)
            return
        messagebox.showinfo("備份完成", f"資料庫：{backup}\n驗證清單：{manifest}", parent=self)

    def run_auto_update(self):
        if not messagebox.askokcancel("一鍵自動更新", "程式將下載官方公開資料、保存原檔、正規化並建立 PROVISIONAL 快照。\n"
                                     "若 TPEx／MOPS 拒絕自動存取，會記錄警告並保留其他已成功步驟。", parent=self):
            return
        results = queue.Queue()
        def worker():
            try:
                report = run_update(self.repository.path, DATA_DIR/"official_pipeline",
                                    date.today().isoformat(), "PROVISIONAL")
                results.put((True, report))
            except Exception as error:
                results.put((False, error))
        def poll():
            try: result = results.get_nowait()
            except queue.Empty:
                self.after(150, poll); return
            if result[0]:
                self._load_latest_snapshot(); self._refresh_source_labels(); self.show_quality()
                warnings = "\n".join(result[1].get("warnings", [])) or "無"
                messagebox.showinfo("自動更新完成", f"完成步驟：{len(result[1]['steps'])}\n警告：{warnings}", parent=self)
            else:
                messagebox.showerror("自動更新失敗", str(result[1]), parent=self)
        threading.Thread(target=worker, daemon=True).start(); self.after(150, poll)

    def export_csv(self):
        path = filedialog.asksaveasfilename(
            title="匯出排行榜",
            defaultextension=".csv",
            filetypes=[("CSV 檔案", "*.csv")],
            initialfile="rankings-demo.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["模型排名","同業排名","百分位","代號","名稱","市場","產業","綜合分數","完整度"] + METRICS + ["狀態"])
            for stock in self.filtered:
                writer.writerow(stock[:9] + stock[9] + (stock[10],))
        messagebox.showinfo("匯出完成", f"已儲存至：\n{path}")

    def rebuild_demo_snapshot(self):
        scored = []
        for index, stock in enumerate(STOCKS):
            financial = stock[6] == "金融保險"
            base = 12 + (12-index)
            data = {
                "revenue_yoy": [base, base+2, base+4, base+5, base+7, base+9],
                "operating_margin": [8+index/3, 9+index/3, 10+index/3, 11+index/3],
                "net_profit": [100+index*3, 105+index*3, 110+index*3, 118+index*3],
                "net_profit_yoy": [10, 12, 14, 16],
                "eps": [max(.1, 2-index*.08)]*4,
                "inventory_turnover": [1.2+index*.05]*4,
                "fcf": [10-index/2, 9-index/2, 8-index/2, 7-index/2, 6-index/2, 5-index/2],
            }
            result = self.engine.score_financial(data) if financial else self.engine.score_general(data)
            results = result["results"]
            scored.append(result | {
                "symbol": stock[3], "name": stock[4], "market": stock[5], "industry": stock[6],
                "aa_count": sum(r.grade == "AA" for r in results),
                "a_count": sum(r.grade == "A" for r in results),
            })
        snapshot_id, checksum = self.repository.publish_snapshot(
            "2026-08-25", "FINAL", "TW-RANK-SPEC-v1.2",
            {"source": "DESKTOP_DEMO_FIXTURE", "official": False}, scored,
        )
        self._load_latest_snapshot()
        self._refresh_source_labels()
        messagebox.showinfo(
            "本機快照已建立",
            "已完成 Decimal 規則評分並寫入不可變 SQLite 快照。\n\n"
            f"Snapshot：{snapshot_id[:8]}…\nChecksum：{checksum[:16]}…\n\n"
            "資料來源仍為 DEMO FIXTURE，不能視為官方排名。",
        )

    def import_official_csv(self):
        directory = filedialog.askdirectory(title="選擇包含官方 CSV 的資料夾")
        if not directory:
            return
        dialog = tk.Toplevel(self)
        dialog.title("建立資料快照")
        dialog.geometry("430x230")
        dialog.resizable(False, False)
        frame = tk.Frame(dialog, bg="white", padx=22, pady=20)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="快照日期", bg="white", fg=INK,
                 font=("Microsoft JhengHei", 10, "bold")).pack(anchor="w")
        date_var = tk.StringVar(value="2026-08-25")
        tk.Entry(frame, textvariable=date_var, relief="solid", borderwidth=1).pack(fill="x", ipady=6, pady=(5,12))
        tk.Label(frame, text="狀態", bg="white", fg=INK,
                 font=("Microsoft JhengHei", 10, "bold")).pack(anchor="w")
        status_var = tk.StringVar(value="FINAL")
        ttk.Combobox(frame, textvariable=status_var, state="readonly",
                     values=["FINAL","PROVISIONAL"]).pack(fill="x", pady=(5,14))

        def execute():
            try:
                result = OfficialImportPipeline(self.repository).import_directory(
                    directory, date_var.get().strip(), status_var.get()
                )
            except (ImportValidationError, ValueError, OSError) as error:
                messagebox.showerror("匯入失敗", str(error), parent=dialog)
                return
            dialog.destroy()
            messagebox.showinfo(
                "匯入完成",
                f"證券：{result['securities']} 檔\n"
                f"財務事實：{result['facts']} 筆\n"
                f"正式可排名：{result['ranked']} 檔\n"
                f"Snapshot：{result['snapshot_id'][:8]}…",
                parent=self,
            )
            self._load_latest_snapshot()
            self._refresh_source_labels()
            if self.current_view == "排行榜":
                self.show_ranking()

        tk.Button(frame, text="驗證並建立不可變快照", bg=NAVY, fg="white",
                  relief="flat", command=execute).pack(fill="x", ipady=6)

    def sync_official_raw(self):
        if not messagebox.askokcancel(
            "同步官方原始資料",
            "將連線證交所 OpenAPI，下載公司主檔、月營收及各業別財報原始 JSON。\n\n"
            "原檔只進 Bronze 快取並保存 SHA-256；在欄位映射與品質驗證完成前，不會直接發布排名。",
            parent=self,
        ):
            return
        self.demo_label.configure(text="官方資料同步中…", bg="#EAF4FB", fg="#245F87")

        results = queue.Queue()

        def worker():
            try:
                run_dir, manifest = TwseOpenApiRawAdapter(DATA_DIR / "official_raw").sync()
                results.put((True, run_dir, manifest))
            except Exception as error:
                results.put((False, error, None))

        def finished(result):
            self._refresh_source_labels()
            if result[0]:
                rows = sum(item["rows"] for item in result[2]["datasets"])
                silver_dir = DATA_DIR / "official_silver" / result[1].name
                try:
                    normalization = normalize_twse_bronze(result[1], silver_dir)
                    silver_text = (f"\nSilver 匯入包：{silver_dir}\n"
                                   f"公司：{normalization['securities']:,}｜營收事實：{normalization['revenue_facts']:,}")
                except (OSError, ValueError, json.JSONDecodeError) as error:
                    silver_text = f"\nSilver 轉換未完成：{error}"
                messagebox.showinfo(
                    "官方原始資料同步完成",
                    f"資料集：{len(result[2]['datasets'])} 組\n總列數：{rows:,}\n"
                    f"保存位置：{result[1]}{silver_text}\n\n"
                    "季報 taxonomy 尚未完整映射，因此 Silver 包標記 PARTIAL，不會直接改寫 FINAL 排名。",
                    parent=self,
                )
            else:
                messagebox.showerror(
                    "同步失敗",
                    f"無法連線或官方回傳格式異常：\n{result[1]}\n\n可改用『匯入官方 CSV』離線流程。",
                    parent=self,
                )

        def poll():
            try:
                result = results.get_nowait()
            except queue.Empty:
                self.after(120, poll)
            else:
                finished(result)

        threading.Thread(target=worker, daemon=True).start()
        self.after(120, poll)


def run_self_test():
    """Headless packaged-app check used by native release builders."""
    with tempfile.TemporaryDirectory(prefix="six-financial-rank-") as temp_dir:
        repository = LocalRepository(Path(temp_dir) / "self_test.db")
        engine = RankingEngine()
        assert repository.latest_snapshot(status=None) is None
        assert engine is not None
        repository.close()
    assert ASSET_DIR.exists(), f"missing bundled assets: {ASSET_DIR}"
    print("SixFinancialRank self-test: OK")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        run_self_test()
        raise SystemExit(0)
    app = RankDesktop()
    app.mainloop()
