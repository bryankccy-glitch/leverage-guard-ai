"""現股當日沖銷計算。與融資計算完全分開，不使用維持率或追繳機制。

依據：
- 有價證券當日沖銷交易作業辦法 第 1 條：相同數量部分相抵，按沖銷後差價辦理款項交割。
- 同辦法 第 7–9、13 條：先賣後買未完成反向買進 → 借券、次一營業日強制買回，費用與價差由委託人負擔。
- 證券交易稅條例 第 2 條（千分之三）、第 2-2 條（同數量現沖，千分之一點五，期間至民國 116 年 12 月 31 日）。
稅率由規則引擎依成交日期決定後傳入，本模組不寫死稅率。

未沖銷的「先買」部位回到一般交割：須支付該部分買進價金與手續費。
交割期限、違約認定由規則引擎與時間軸處理；本模組只計算「估計資金缺口」，不判定違約。
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .fees import FeeSchedule, brokerage_fee, transaction_tax
from .rounding import CALCULATION_VERSION, ZERO, money
from .types import CalcWarning, Metric
from .validation import Validator


@dataclass
class DayTradeInput:
    direction: str  # "buy_first" | "sell_first"
    buy_price: Decimal
    buy_quantity: Decimal
    sell_price: Decimal
    sell_quantity: Decimal
    day_trade_tax_rate: Decimal  # 規則引擎提供
    general_tax_rate: Decimal  # 規則引擎提供
    available_cash: Decimal = ZERO
    fees: FeeSchedule = FeeSchedule()
    # 先賣後買未買回時的假設（強制買回價格、借券費率）；沒有就不估算並列為缺少資訊
    assumed_buyback_price: Decimal | None = None
    assumed_borrow_fee_rate: Decimal | None = None
    asset_label: str = "模擬資產"


@dataclass
class DayTradeResult:
    calculation_version: str
    metrics: dict[str, Metric]
    warnings: list[CalcWarning]
    assumptions: list[str]
    facts: dict[str, object]


def _validate(i: DayTradeInput) -> None:
    v = Validator()
    if i.direction not in ("buy_first", "sell_first"):
        v.add("direction", "invalid", "交易方向只能是先買後賣或先賣後買")
    v.positive("buy_price", i.buy_price, "買進價格")
    v.positive("sell_price", i.sell_price, "賣出價格")
    for name, label in (("buy_quantity", "買進股數"), ("sell_quantity", "賣出股數")):
        v.non_negative(name, getattr(i, name), label)
        v.integer(name, getattr(i, name), label)
    if i.buy_quantity == ZERO and i.sell_quantity == ZERO:
        v.add("buy_quantity", "required", "買進或賣出股數至少一項大於 0")
    if i.direction == "buy_first" and i.buy_quantity == ZERO:
        v.add("buy_quantity", "required", "先買後賣必須有買進股數")
    if i.direction == "sell_first" and i.sell_quantity == ZERO:
        v.add("sell_quantity", "required", "先賣後買必須有賣出股數")
    v.non_negative("available_cash", i.available_cash, "可用交割資金")
    v.rate("day_trade_tax_rate", i.day_trade_tax_rate, "當沖稅率", Decimal("0.01"))
    v.rate("general_tax_rate", i.general_tax_rate, "一般稅率", Decimal("0.01"))
    v.rate("assumed_borrow_fee_rate", i.assumed_borrow_fee_rate, "借券費率", Decimal("0.07"))
    v.raise_if_any()


def calculate_day_trade(i: DayTradeInput) -> DayTradeResult:
    _validate(i)
    warnings: list[CalcWarning] = []
    matched = min(i.buy_quantity, i.sell_quantity)
    unmatched_long = i.buy_quantity - matched  # 先買後賣，沒賣掉的部分
    unmatched_short = i.sell_quantity - matched  # 先賣後買，沒買回的部分

    buy_amount = money(i.buy_price * i.buy_quantity)
    sell_amount = money(i.sell_price * i.sell_quantity)
    buy_fee = brokerage_fee(buy_amount, i.fees)
    sell_fee = brokerage_fee(sell_amount, i.fees)
    matched_sell_amount = money(i.sell_price * matched)
    unmatched_sell_amount = sell_amount - matched_sell_amount
    tax_dt = transaction_tax(matched_sell_amount, i.day_trade_tax_rate)
    tax_general = transaction_tax(unmatched_sell_amount, i.general_tax_rate)
    gross_matched = money((i.sell_price - i.buy_price) * matched)

    # 手續費按股數比例分攤到已沖銷部分，用來計算沖銷損益
    def share(total: Decimal, part: Decimal, whole: Decimal) -> Decimal:
        return ZERO if whole == ZERO else money(total * part / whole)

    matched_fees = share(buy_fee, matched, i.buy_quantity) + share(sell_fee, matched, i.sell_quantity)
    net_matched = gross_matched - matched_fees - tax_dt

    # 交割應付（＋）／應收（−）：已沖銷部分只交割差價；未沖銷的買進部分要付全額
    long_leg_payable = money(i.buy_price * unmatched_long) + share(buy_fee, unmatched_long, i.buy_quantity)
    settlement_payable = long_leg_payable - net_matched
    if unmatched_short > ZERO:
        # 未買回的賣出：賣出價款原本可收，但會被強制買回；先列入應收，另估強制買回成本
        settlement_payable -= unmatched_sell_amount - share(sell_fee, unmatched_short, i.sell_quantity) - tax_general
    funding_gap = max(ZERO, settlement_payable - i.available_cash)

    buyback_cost = None
    if unmatched_short > ZERO:
        if i.assumed_buyback_price is not None and i.assumed_borrow_fee_rate is not None:
            bb_amount = money(i.assumed_buyback_price * unmatched_short)
            borrow_fee = money(i.assumed_buyback_price * unmatched_short * i.assumed_borrow_fee_rate)
            buyback_cost = bb_amount + brokerage_fee(bb_amount, i.fees) + borrow_fee
        else:
            warnings.append(CalcWarning("missing_buyback_assumption",
                                        "先賣後買未買回：未提供強制買回價格與借券費率假設，無法估算強制買回成本"))
    if unmatched_long > ZERO:
        warnings.append(CalcWarning("unmatched_long",
                                    f"有 {unmatched_long} 股買進未在當日賣出，這部分需以全額價金辦理交割"))
    if funding_gap > ZERO:
        warnings.append(CalcWarning("funding_gap",
                                    "估計交割資金不足。這是預估，不代表已發生違約；是否違約依交割期限與券商確認"))

    m = {
        "buy_amount": Metric("buy_amount", "買進總金額", buy_amount, "TWD", "買進價格 × 買進股數",
                             {"價格": str(i.buy_price), "股數": str(i.buy_quantity)}),
        "sell_amount": Metric("sell_amount", "賣出總金額", sell_amount, "TWD", "賣出價格 × 賣出股數",
                              {"價格": str(i.sell_price), "股數": str(i.sell_quantity)}),
        "matched_quantity": Metric("matched_quantity", "已沖銷股數", matched, "shares", "min(買進股數, 賣出股數)", {},
                                   ["DT-DEFINITION"]),
        "unmatched_long": Metric("unmatched_long", "未沖銷股數（買進未賣出）", unmatched_long, "shares",
                                 "買進股數 − 已沖銷股數", {}, ["DT-UNMATCHED-LONG"]),
        "unmatched_short": Metric("unmatched_short", "未沖銷股數（賣出未買回）", unmatched_short, "shares",
                                  "賣出股數 − 已沖銷股數", {}, ["DT-SELL-FIRST-BUYIN"]),
        "gross_pnl": Metric("gross_pnl", "已沖銷毛損益", gross_matched, "TWD", "(賣出價格 − 買進價格) × 已沖銷股數", {}),
        "fees": Metric("fees", "手續費合計", buy_fee + sell_fee, "TWD", "買進手續費 ＋ 賣出手續費",
                       {"買進": str(buy_fee), "賣出": str(sell_fee)}),
        "tax_day_trade": Metric("tax_day_trade", "當沖交易稅（已沖銷部分）", tax_dt, "TWD", "已沖銷賣出金額 × 當沖稅率",
                                {"稅率": str(i.day_trade_tax_rate)}, ["TAX-DAYTRADE"]),
        "tax_general": Metric("tax_general", "一般交易稅（未沖銷賣出）", tax_general, "TWD", "未沖銷賣出金額 × 一般稅率",
                              {"稅率": str(i.general_tax_rate)}, ["TAX-GENERAL"],
                              note="未完成同數量沖銷的賣出，不適用當沖減半稅率"),
        "net_pnl": Metric("net_pnl", "已沖銷淨損益", net_matched, "TWD", "毛損益 − 分攤手續費 − 當沖交易稅", {}),
        "settlement_payable": Metric("settlement_payable", "估計交割應付款", settlement_payable, "TWD",
                                     "未沖銷買進價金與手續費 − 已沖銷淨損益 − 未買回賣出價款淨額", {},
                                     ["DT-SETTLEMENT-CYCLE"], simplified=True, note="負數代表應收"),
        "funding_gap": Metric("funding_gap", "估計資金缺口", funding_gap, "TWD",
                              "max(0, 交割應付款 − 可用交割資金)", {"可用資金": str(i.available_cash)},
                              ["DT-FUNDING-GAP"], simplified=True, note="預估值，不等於違約"),
        "estimated_buyback_cost": Metric("estimated_buyback_cost", "估計強制買回成本", buyback_cost, "TWD",
                                         "假設買回價 × 未買回股數 ＋ 手續費 ＋ 借券費",
                                         {"假設買回價": str(i.assumed_buyback_price),
                                          "假設借券費率": str(i.assumed_borrow_fee_rate)},
                                         ["DT-SELL-FIRST-COSTS"], simplified=True,
                                         note="借券費率上限為收盤價 7%（作業辦法第 7 條），實際依當日標借結果"),
    }
    assumptions = [
        f"資產：{i.asset_label}（模擬）",
        "手續費依股數比例分攤到已沖銷與未沖銷部分",
        "假設券商已依規定在成交當日申報沖銷（作業辦法第 14 條：未申報者視為不予沖銷）",
    ]
    facts = {
        "trading_type": "day_trading",
        "direction": i.direction,
        "matched_quantity": matched,
        "unmatched_long": unmatched_long,
        "unmatched_short": unmatched_short,
        "funding_gap": funding_gap,
        "settlement_payable": settlement_payable,
        "net_pnl": net_matched,
    }
    return DayTradeResult(CALCULATION_VERSION, m, warnings, assumptions, facts)
