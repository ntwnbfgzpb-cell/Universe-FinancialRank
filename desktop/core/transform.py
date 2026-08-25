from __future__ import annotations

from decimal import Decimal

D = Decimal


def decimal_or_none(value):
    if value in (None, ""):
        return None
    return value if isinstance(value, Decimal) else D(str(value))


def cumulative_to_quarters(cumulative_by_quarter):
    """Convert Q1/H1/9M/FY cumulative facts to standalone quarters."""
    result, previous = {}, None
    for quarter in (1, 2, 3, 4):
        current = decimal_or_none(cumulative_by_quarter.get(quarter))
        if current is None:
            result[quarter] = None
        elif quarter == 1:
            result[quarter] = current
        elif previous is None:
            result[quarter] = None
        else:
            result[quarter] = current - previous
        previous = current
    return result


def safe_ratio(numerator, denominator, multiplier=1):
    numerator, denominator = decimal_or_none(numerator), decimal_or_none(denominator)
    if numerator is None or denominator in (None, D(0)):
        return None
    return numerator / denominator * D(str(multiplier))


def revenue_growth(current, comparison):
    ratio = safe_ratio(current, comparison)
    return None if ratio is None else (ratio - D(1)) * D(100)


def inventory_turnover(cost_of_goods_sold, inventory_begin, inventory_end):
    begin, end = decimal_or_none(inventory_begin), decimal_or_none(inventory_end)
    if begin is None or end is None:
        return None
    average = (begin + end) / D(2)
    return safe_ratio(cost_of_goods_sold, average)


def core_fcf(cfo, capex_ppe, capex_intangible):
    cfo = decimal_or_none(cfo)
    if cfo is None:
        return None
    ppe = abs(decimal_or_none(capex_ppe) or D(0))
    intangible = abs(decimal_or_none(capex_intangible) or D(0))
    return cfo - ppe - intangible
