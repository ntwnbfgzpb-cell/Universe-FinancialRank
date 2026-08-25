from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable, Mapping, Sequence

from .rules import load_rule_manifest

D = Decimal
SCORES = {"AA": D(4), "A": D(3), "BB": D(2), "B": D(1), "C": D(0)}


def dec(value) -> Decimal:
    return value if isinstance(value, Decimal) else D(str(value))


@dataclass(frozen=True)
class TraceStep:
    rule_id: str
    matched: bool
    detail: str


@dataclass(frozen=True)
class GradeResult:
    metric_code: str
    grade: str
    score: Decimal | None
    rule_id: str
    reason_text: str
    inputs: Mapping[str, object]
    quality_flags: tuple[str, ...] = ()
    decision_trace: tuple[TraceStep, ...] = ()


def _result(metric, grade, rule, reason, inputs, trace, flags=()):
    return GradeResult(metric, grade, SCORES.get(grade), rule, reason, inputs, tuple(flags), tuple(trace))


def revenue_growth(yoy: Sequence, lunar_excluded: bool = False) -> GradeResult:
    metric = "REV_GROWTH"
    vals = tuple(dec(v) for v in yoy)
    inputs = {"yoy": tuple(str(v) for v in vals)}
    if len(vals) < 6:
        return GradeResult(metric, "N/A", None, "NA-REV-DATA", "最近六個完整月份資料不足", inputs, ("INSUFFICIENT_DATA",))
    vals = vals[-6:]
    avg = sum(vals) / D(6)
    last, prior = vals[-1], vals[-2]
    avg_latest = sum(vals[-3:]) / D(3)
    avg_prior = sum(vals[:3]) / D(3)
    decreasing = vals[-3] > vals[-2] > vals[-1]
    slowdown = None
    if prior > 0:
        slowdown = (prior - last) / max(abs(prior), D("10"))
    checks = [
        ("C-REV-01", avg < 0 or (last < 0 and not lunar_excluded), "六個月平均或最近月年增率為負"),
        ("B-REV-01", avg > 0 and decreasing, "最近三個月年增率連續遞減"),
        ("AA-REV-01", all(v > 0 for v in vals) and avg > 25 and last >= 0 and avg_latest >= avg_prior,
         "六個月皆為正、平均超過 25%，且三月動能未放緩"),
        ("A-REV-01", all(v > 0 for v in vals) and D(10) <= avg <= D(25) and last >= 0,
         "六個月皆為正且平均介於 10% 至 25%"),
        ("A-REV-02", avg > 25 and last >= 0 and slowdown is not None and D(0) < slowdown <= D("0.5"),
         "平均高於 25%，最近月非負且相對放緩不超過 50%"),
        ("BB-REV-01", any(v < 0 for v in vals), "六個月內曾出現負成長"),
        ("BB-REV-99", True, "資料完整但未命中其他規則"),
    ]
    grades = {"C-REV-01":"C","B-REV-01":"B","AA-REV-01":"AA","A-REV-01":"A","A-REV-02":"A","BB-REV-01":"BB","BB-REV-99":"BB"}
    trace = []
    for rule, matched, detail in checks:
        trace.append(TraceStep(rule, matched, detail))
        if matched:
            return _result(metric, grades[rule], rule, detail, inputs | {"average": str(avg)}, trace)
    raise AssertionError


def operating_margin(values: Sequence, metric_code="OP_MARGIN_GENERAL") -> GradeResult:
    vals = tuple(dec(v) for v in values)
    inputs = {"quarterly_margin": tuple(str(v) for v in vals)}
    if len(vals) < 4:
        return GradeResult(metric_code, "N/A", None, "NA-OPM-DATA", "最近四個單季資料不足", inputs, ("INSUFFICIENT_DATA",))
    vals = vals[-4:]
    avg = sum(vals) / D(4)
    declines = [a > 0 and (a-b)/abs(a) >= D(".2") for a,b in zip(vals, vals[1:])]
    checks = [
        ("C-OPM-01", avg < 0 or vals[-1] < 0, "四季平均或最近一季為負"),
        ("B-OPM-01", declines[-1] or avg <= 5, "最近一季大幅下降或四季平均不高於 5%"),
        ("AA-OPM-01", not any(declines) and avg >= 15, "四季未大幅下降且平均至少 15%"),
        ("AA-OPM-02", not any(declines) and 10 <= avg < 15 and vals[-1] > vals[-2], "平均 10% 至 15% 且最近季改善"),
        ("A-OPM-01", not any(declines) and 10 <= avg < 15, "平均 10% 至 15%"),
        ("A-OPM-02", not any(declines) and 5 < avg < 10 and vals[-1] > vals[-2], "平均 5% 至 10% 且最近季改善"),
        ("BB-OPM-01", any(declines[:-1]), "過去四季曾大幅下降"),
        ("BB-OPM-99", True, "資料完整但未命中其他規則"),
    ]
    grades = {"C-OPM-01":"C","B-OPM-01":"B","AA-OPM-01":"AA","AA-OPM-02":"AA","A-OPM-01":"A","A-OPM-02":"A","BB-OPM-01":"BB","BB-OPM-99":"BB"}
    trace=[]
    for rule, matched, detail in checks:
        trace.append(TraceStep(rule, matched, detail))
        if matched:
            return _result(metric_code, grades[rule], rule, detail, inputs | {"average": str(avg)}, trace)
    raise AssertionError


def net_profit_growth(profits: Sequence, yoy: Sequence | None = None) -> GradeResult:
    metric = "NET_PROFIT_GROWTH"
    vals = tuple(dec(v) for v in profits)
    yoy_vals = tuple(dec(v) for v in yoy) if yoy else ()
    inputs = {"profits": tuple(str(v) for v in vals), "yoy": tuple(str(v) for v in yoy_vals)}
    if len(vals) < 4:
        return GradeResult(metric, "N/A", None, "NA-NP-DATA", "最近四季資料不足", inputs, ("INSUFFICIENT_DATA",))
    vals = vals[-4:]
    last_yoy = yoy_vals[-1] if yoy_vals else D(0)
    decline_50 = vals[-2] > 0 and (vals[-2]-vals[-1])/abs(vals[-2]) >= D(".5")
    checks = [
        ("C-NP-01", vals[-1] < 0 and vals[-2] < 0, "最近兩季皆為負"),
        ("B-NP-01", vals[-1] < 0 or sum(v < 0 for v in vals) >= 2 or (vals[-3] > vals[-2] > vals[-1] and last_yoy < 50),
         "最近一季為負、四季至少兩季為負，或最近三季連減"),
        ("AA-NP-01", all(v > 0 for v in vals[-3:]) and vals[-1] > vals[-2], "最近三季為正且最近季改善"),
        ("AA-NP-02", len(yoy_vals) >= 3 and all(v > 0 for v in vals[-3:]) and all(v >= 50 for v in yoy_vals[-3:]),
         "最近三季為正且年增率皆至少 50%"),
        ("A-NP-01", vals[-1] > 0 and vals[-2] > 0 and not decline_50, "最近兩季為正且最近季未大幅季減"),
        ("BB-NP-01", vals[-1] > 0 and vals[-2] > 0 and decline_50, "最近兩季為正但最近季大幅季減"),
        ("BB-NP-02", vals[-2] < 0 and vals[-1] > 0, "最近一季由負轉正"),
        ("BB-NP-99", True, "資料完整但未命中其他規則"),
    ]
    grades = {"C-NP-01":"C","B-NP-01":"B","AA-NP-01":"AA","AA-NP-02":"AA","A-NP-01":"A","BB-NP-01":"BB","BB-NP-02":"BB","BB-NP-99":"BB"}
    trace=[]
    for rule, matched, detail in checks:
        trace.append(TraceStep(rule, matched, detail))
        if matched:
            return _result(metric, grades[rule], rule, detail, inputs, trace)
    raise AssertionError


def eps_profitability(quarterly_eps: Sequence) -> GradeResult:
    metric = "EPS_TTM"
    vals = tuple(dec(v) for v in quarterly_eps)
    inputs = {"quarterly_eps": tuple(str(v) for v in vals)}
    if len(vals) < 4:
        return GradeResult(metric, "N/A", None, "NA-EPS-DATA", "最近四季 EPS 資料不足", inputs, ("INSUFFICIENT_DATA",))
    vals = vals[-4:]
    ttm = sum(vals)
    if ttm < 0 or vals[-1] < 0:
        grade, rule = "C", "C-EPS-01"
    elif ttm > 5:
        grade, rule = "AA", "AA-EPS-01"
    elif ttm >= 3:
        grade, rule = "A", "A-EPS-01"
    elif ttm >= 1:
        grade, rule = "BB", "BB-EPS-01"
    else:
        grade, rule = "B", "B-EPS-01"
    reason = f"最近四季累積 EPS 為 {ttm}，依原始精度判定"
    return _result(metric, grade, rule, reason, inputs | {"ttm_eps": str(ttm)}, [TraceStep(rule, True, reason)])


def inventory_turnover(values: Sequence, applicable=True) -> GradeResult:
    metric = "INVENTORY_TURNOVER_Q"
    vals = tuple(dec(v) for v in values)
    inputs = {"quarterly_turnover": tuple(str(v) for v in vals)}
    if not applicable:
        return GradeResult(metric, "N/A", None, "NA-ITR-01", "產業或財報口徑不適用存貨週轉", inputs, ("NOT_APPLICABLE",))
    if len(vals) < 4:
        return GradeResult(metric, "N/A", None, "NA-ITR-DATA", "最近四季資料不足", inputs, ("INSUFFICIENT_DATA",))
    vals = vals[-4:]
    declines = [a > 0 and (a-b)/abs(a) >= D(".2") for a,b in zip(vals, vals[1:])]
    cumulative_decline = vals[-3] > 0 and (vals[-3]-vals[-1])/abs(vals[-3]) >= D(".2")
    avg = sum(vals)/D(4)
    checks = [
        ("C-ITR-01", declines[-1], "最近一季較前季下降至少 20%"),
        ("B-ITR-01", any(declines[:-1]), "過去四季曾出現單季下降至少 20%"),
        ("BB-ITR-01", vals[-3] > vals[-2] > vals[-1] and cumulative_decline, "連續兩季下降且累積降幅至少 20%"),
        ("AA-ITR-01", not any(declines) and avg > D("1.5"), "四季穩定且平均超過 1.5 次"),
        ("A-ITR-01", not any(declines) and avg <= D("1.5"), "四季穩定且平均不超過 1.5 次"),
    ]
    grades={"C-ITR-01":"C","B-ITR-01":"B","BB-ITR-01":"BB","AA-ITR-01":"AA","A-ITR-01":"A"}
    trace=[]
    for rule, matched, detail in checks:
        trace.append(TraceStep(rule, matched, detail))
        if matched:
            return _result(metric, grades[rule], rule, detail, inputs | {"average":str(avg)}, trace)
    return _result(metric, "BB", "BB-ITR-99", "資料完整但未命中其他規則", inputs, trace)


def free_cash_flow(values: Sequence, applicable=True) -> GradeResult:
    metric = "CORE_FCF"
    vals = tuple(dec(v) for v in values)
    inputs = {"quarterly_fcf": tuple(str(v) for v in vals)}
    if not applicable:
        return GradeResult(metric, "N/A", None, "NA-FCF-01", "金融業模型不適用 Core FCF", inputs, ("NOT_APPLICABLE",))
    if len(vals) < 6:
        return GradeResult(metric, "N/A", None, "NA-FCF-DATA", "最近六季資料不足", inputs, ("INSUFFICIENT_DATA",))
    vals = vals[-6:]
    sum6, sum4 = sum(vals), sum(vals[-4:])
    if all(v > 0 for v in vals):
        grade, rule = "AA", "AA-FCF-01"
    elif sum6 >= 0 and sum4 >= 0:
        grade, rule = "A", "A-FCF-01"
    elif sum6 < 0 <= sum4:
        grade, rule = "BB", "BB-FCF-01"
    elif sum6 >= 0 > sum4:
        grade, rule = "B", "B-FCF-01"
    else:
        grade, rule = "C", "C-FCF-01"
    reason = f"六季累計 {sum6}；四季累計 {sum4}"
    return _result(metric, grade, rule, reason, inputs | {"sum6":str(sum6),"sum4":str(sum4)}, [TraceStep(rule, True, reason)])


def overall(results: Iterable[GradeResult], minimum=4):
    valid = [result for result in results if result.score is not None]
    if len(valid) < minimum:
        return None, len(valid), "INSUFFICIENT_DATA"
    return sum(result.score for result in valid) / D(len(valid)), len(valid), "RANKED"


class RankingEngine:
    def __init__(self, rules_path=None):
        self.rule_manifest = load_rule_manifest(rules_path)
        self.rule_version = self.rule_manifest["version"]
        self.rule_checksum = self.rule_manifest["checksum"]

    def score_general(self, data: Mapping[str, Sequence]):
        results = (
            revenue_growth(data.get("revenue_yoy", ())),
            operating_margin(data.get("operating_margin", ())),
            net_profit_growth(data.get("net_profit", ()), data.get("net_profit_yoy", ())),
            eps_profitability(data.get("eps", ())),
            inventory_turnover(data.get("inventory_turnover", ()), data.get("inventory_applicable", True)),
            free_cash_flow(data.get("fcf", ()), data.get("fcf_applicable", True)),
        )
        score, count, status = overall(results, 4)
        return {"model_code":"TW6F_GENERAL", "results":results, "overall_score":score, "valid_count":count, "rank_status":status}

    def score_financial(self, data: Mapping[str, Sequence], securities=False):
        margin_code = "OP_MARGIN_SECURITIES" if securities else "PRETAX_MARGIN_FINANCIAL"
        results = (
            revenue_growth(data.get("revenue_yoy", ())),
            operating_margin(data.get("operating_margin", ()), margin_code),
            net_profit_growth(data.get("net_profit", ()), data.get("net_profit_yoy", ())),
            eps_profitability(data.get("eps", ())),
            inventory_turnover((), False),
            free_cash_flow((), False),
        )
        score, count, status = overall(results[:4], 4)
        return {"model_code":"TW4F_SECURITIES" if securities else "TW4F_FINANCIAL",
                "results":results, "overall_score":score, "valid_count":count, "rank_status":status}
