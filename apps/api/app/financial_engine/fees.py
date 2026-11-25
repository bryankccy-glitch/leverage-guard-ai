"""交易手續費與證券交易稅。

- 手續費：成交金額 × 費率 × 折扣，未滿最低手續費以最低手續費計。費率上限與折扣依券商契約，這裡是可調參數。
- 證券交易稅：由賣方負擔，稅率由規則引擎依交易類型與日期決定（證券交易稅條例第 2 條、第 2-2 條）。
- 進位方式（預設無條件捨去到元）是常見實務作法，屬可調整的假設，不是法規強制。
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .rounding import ZERO, D, money


@dataclass(frozen=True)
class FeeSchedule:
    fee_rate: Decimal = D("0.001425")
    fee_discount: Decimal = D("1")
    min_fee: Decimal = D("20")
    rounding: str = "down"


def brokerage_fee(amount: Decimal, schedule: FeeSchedule) -> Decimal:
    if amount <= ZERO:
        return ZERO
    fee = money(amount * schedule.fee_rate * schedule.fee_discount, schedule.rounding)
    return max(fee, schedule.min_fee)


def transaction_tax(sell_amount: Decimal, tax_rate: Decimal, rounding: str = "down") -> Decimal:
    if sell_amount <= ZERO:
        return ZERO
    return money(sell_amount * tax_rate, rounding)
