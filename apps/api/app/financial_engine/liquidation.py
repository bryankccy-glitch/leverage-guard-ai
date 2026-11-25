"""模擬擔保品處分：處分後是溢額返還，還是仍有剩餘債務。

依「證券商辦理有價證券買賣融資融券業務操作辦法」第 55 條第 2 項、第 81 條：
處分後如有溢額應予發還；如不足抵償債務，以信用帳戶內其他款項抵充，仍不足者通知委託人補足。

剩餘債務＝max(0, 未清償借款＋利息＋違約金＋處分成本 − 處分淨所得 − 可抵充款項)
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .fees import FeeSchedule, brokerage_fee, transaction_tax
from .rounding import ZERO, money
from .types import Metric
from .validation import Validator


@dataclass
class DisposalInput:
    quantity: Decimal
    disposal_price: Decimal
    outstanding_debt: Decimal
    accrued_interest: Decimal = ZERO
    penalty: Decimal = ZERO
    other_account_credits: Decimal = ZERO
    fees: FeeSchedule = FeeSchedule()
    sell_tax_rate: Decimal = Decimal("0.003")
    filled_quantity: Decimal | None = None  # 流動性不足時只成交部分股數


def simulate_disposal(i: DisposalInput) -> dict[str, Metric]:
    v = Validator()
    v.positive("quantity", i.quantity, "處分股數")
    v.positive("disposal_price", i.disposal_price, "處分價格")
    v.non_negative("outstanding_debt", i.outstanding_debt, "未清償借款")
    for name in ("accrued_interest", "penalty", "other_account_credits"):
        v.non_negative(name, getattr(i, name), name)
    if i.filled_quantity is not None and not (ZERO <= i.filled_quantity <= i.quantity):
        v.add("filled_quantity", "out_of_range", "成交股數必須介於 0 與處分股數之間")
    v.raise_if_any()

    filled = i.quantity if i.filled_quantity is None else i.filled_quantity
    gross = money(i.disposal_price * filled)
    sell_fee = brokerage_fee(gross, i.fees)
    tax = transaction_tax(gross, i.sell_tax_rate)
    net_proceeds = gross - sell_fee - tax if gross > ZERO else ZERO
    total_debt = i.outstanding_debt + i.accrued_interest + i.penalty
    remaining = max(ZERO, total_debt - net_proceeds - i.other_account_credits)
    surplus = max(ZERO, net_proceeds + i.other_account_credits - total_debt)
    unfilled = i.quantity - filled
    return {
        "disposal_gross": Metric("disposal_gross", "處分成交金額", gross, "TWD", "處分價格 × 成交股數",
                                 {"處分價格": str(i.disposal_price), "成交股數": str(filled)}, simplified=True),
        "disposal_costs": Metric("disposal_costs", "處分手續費與交易稅", sell_fee + tax, "TWD",
                                 "賣出手續費 ＋ 證券交易稅", {}, ["TAX-GENERAL"], simplified=True),
        "net_proceeds": Metric("net_proceeds", "處分淨所得", net_proceeds, "TWD", "處分成交金額 − 處分成本", {}),
        "total_debt": Metric("total_debt", "應清償債務合計", total_debt, "TWD", "融資借款 ＋ 利息 ＋ 違約金",
                             {"利息": str(i.accrued_interest), "違約金": str(i.penalty)}),
        "remaining_debt": Metric("remaining_debt", "可能的剩餘債務", remaining, "TWD",
                                 "max(0, 應清償債務 − 處分淨所得 − 可抵充款項)",
                                 {"可抵充款項": str(i.other_account_credits)}, ["MARGIN-DISPOSAL-SHORTFALL"],
                                 simplified=True, note="實際金額以券商結算為準"),
        "surplus_returned": Metric("surplus_returned", "應發還溢額", surplus, "TWD",
                                   "max(0, 處分淨所得 ＋ 可抵充款項 − 應清償債務)", {}, ["MARGIN-DISPOSAL-SURPLUS"],
                                   simplified=True),
        "unfilled_quantity": Metric("unfilled_quantity", "未成交股數", unfilled, "shares", "處分股數 − 成交股數", {},
                                    ["MARGIN-LIQUIDITY-FAILURE"]),
    }
