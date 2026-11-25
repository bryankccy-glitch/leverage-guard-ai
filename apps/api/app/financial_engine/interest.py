"""融資利息：本金 × 年利率 × 計息天數 ÷ 年基準天數。

各券商的計息天數算法（算頭不算尾、以交割日起算等）與年基準（365/360）依契約而定，
這裡把兩者都做成參數，不假設所有券商一致。
"""
from __future__ import annotations

from decimal import Decimal

from .rounding import ZERO, money


def financing_interest(principal: Decimal, annual_rate: Decimal | None, days: int,
                       day_basis: int = 365, rounding: str = "half_up") -> Decimal | None:
    if annual_rate is None:
        return None
    if principal <= ZERO or days <= 0:
        return ZERO
    return money(principal * annual_rate * Decimal(days) / Decimal(day_basis), rounding)
