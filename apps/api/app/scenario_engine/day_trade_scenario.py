"""當沖情境：計算＋規則引擎＋時間軸。稅率依成交日期由規則引擎決定。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from ..financial_engine.day_trading import DayTradeInput, calculate_day_trade
from ..financial_engine.fees import FeeSchedule
from ..financial_engine.rounding import ZERO, D
from ..financial_engine.types import serialize
from ..legal_rules.engine import evaluate, param, rule_version_label, select_rules
from ..timeline_engine.builder import TimelineBuilder
from ..timeline_engine.trading_calendar import add_trading_days, is_trading_day


@dataclass
class DayTradeScenarioInput:
    direction: str
    buy_price: Decimal
    buy_quantity: Decimal
    sell_price: Decimal
    sell_quantity: Decimal
    trade_date: date
    available_cash: Decimal = ZERO
    fees: FeeSchedule = field(default_factory=FeeSchedule)
    assumed_buyback_price: Decimal | None = None
    assumed_borrow_fee_rate: Decimal | None = None
    asset_label: str = "模擬資產"
    status_overrides: dict[str, str] | None = None


def tax_rates(trade_date: date, status_overrides: dict[str, str] | None = None) -> dict[str, Any]:
    dt = select_rules("day_trading", trade_date, status_overrides=status_overrides).rules
    general = param(dt, "TAX-GENERAL", "rate")
    reduced = param(dt, "TAX-DAYTRADE", "rate")
    return {"general": general or D("0.003"), "day_trade": reduced or general or D("0.003"),
            "day_trade_rule_applied": reduced is not None,
            "note": None if reduced is not None else "成交日期不在當沖減半稅率的適用期間，以一般稅率計算"}


def run_day_trade_scenario(s: DayTradeScenarioInput) -> dict[str, Any]:
    rates = tax_rates(s.trade_date, s.status_overrides)
    result = calculate_day_trade(DayTradeInput(
        direction=s.direction, buy_price=s.buy_price, buy_quantity=s.buy_quantity, sell_price=s.sell_price,
        sell_quantity=s.sell_quantity, day_trade_tax_rate=rates["day_trade"], general_tax_rate=rates["general"],
        available_cash=s.available_cash, fees=s.fees, assumed_buyback_price=s.assumed_buyback_price,
        assumed_borrow_fee_rate=s.assumed_borrow_fee_rate, asset_label=s.asset_label))
    sel = select_rules("day_trading", s.trade_date, status_overrides=s.status_overrides)
    ev = evaluate("day_trading", result.facts, s.trade_date, status_overrides=s.status_overrides)
    tl = TimelineBuilder(sel.rules)
    warnings = list(result.warnings)
    trade_note = None if is_trading_day(s.trade_date) else "成交日期不是交易日，請確認日期"

    m = result.metrics
    tl.add(0, s.trade_date, "trade_executed", "triggered_in_simulation",
           f"{'先買後賣' if s.direction == 'buy_first' else '先賣後買'}：買 {s.buy_quantity} 股、賣 {s.sell_quantity} 股",
           ["DT-DEFINITION", "DT-ELIGIBILITY", "TAX-DAYTRADE" if rates["day_trade_rule_applied"] else "TAX-GENERAL"],
           {"已沖銷股數": m["matched_quantity"].value, "已沖銷淨損益": m["net_pnl"].value},
           uncertainty=[x for x in [trade_note, rates["note"]] if x])
    tl.add(0, s.trade_date, "offset_reported", "potential", "假設券商已於成交當日下午六時前申報沖銷",
           ["DT-REPORTING"], uncertainty=["若券商未申報，視為不予沖銷，全部須全額交割"])

    settle_days = int(param(sel.rules, "DT-SETTLEMENT-CYCLE", "settlement_business_days") or 2)
    settle = add_trading_days(s.trade_date, settle_days)
    if "normal_settlement_obligation" in ev.triggered_events:
        tl.add(1, s.trade_date, "normal_settlement_obligation", "triggered_in_simulation",
               f"{m['unmatched_long'].value} 股買進未在當日賣出", ["DT-UNMATCHED-LONG"],
               {"未沖銷股數": m["unmatched_long"].value})
    if "forced_buy_in" in ev.triggered_events:
        buyin = add_trading_days(s.trade_date, int(param(sel.rules, "DT-SELL-FIRST-BUYIN", "buyin_business_days") or 1))
        tl.add(1, buyin.date, "forced_buy_in", "triggered_in_simulation",
               f"{m['unmatched_short'].value} 股賣出未買回", ["DT-SELL-FIRST-BUYIN"],
               {"未買回股數": m["unmatched_short"].value, "估計強制買回成本": m["estimated_buyback_cost"].value},
               deadline=buyin.date, deadline_note=buyin.note,
               uncertainty=[] if m["estimated_buyback_cost"].value is not None else
               ["未提供強制買回價格與借券費率假設，無法估算成本"])
        pay_by = add_trading_days(buyin.date, 1)
        tl.add(2, pay_by.date, "buyin_cost_due", "potential", "強制買回還券之次一營業日下午五時前",
               ["DT-SELL-FIRST-COSTS"], {"估計強制買回成本": m["estimated_buyback_cost"].value},
               deadline=pay_by.date, deadline_note=(pay_by.note or "") + "（下午五時前）",
               uncertainty=["還券日以強制買回當日全數成交估算；未全數買回時期限會延後"])
    tl.add(3, settle.date, "settlement_due", "potential", f"成交日後第 {settle_days} 個營業日",
           ["DT-SETTLEMENT-CYCLE"], {"估計交割應付款": m["settlement_payable"].value},
           deadline=settle.date, deadline_note=settle.note)
    if "funding_gap_estimated" in ev.triggered_events:
        tl.add(3, settle.date, "funding_gap_estimated", "requires_confirmation",
               "估計交割應付款大於可用交割資金", ["DT-FUNDING-GAP"], {"估計資金缺口": m["funding_gap"].value},
               uncertainty=["這是預估資金缺口，不是違約。交割日前補足即可；是否構成違約交割，以券商確認為準"])
    general_rules = select_rules("general", s.trade_date, status_overrides=s.status_overrides).rules
    tl.rules.update(general_rules)
    tl.add(4, None, "dispute_available", "potential", "對處理結果有疑義時", ["GENERAL-DISPUTE"])
    return {
        "trading_type": "day_trading",
        "calculation_version": result.calculation_version,
        "rule_version": rule_version_label(sel.rules),
        "rule_versions": {k: v.version for k, v in sel.rules.items()},
        "rule_conflicts": sel.conflicts,
        "parameters": {"day_trade_tax_rate": str(rates["day_trade"]), "general_tax_rate": str(rates["general"]),
                       "settlement_business_days": str(settle_days), "settlement_date": settle.date.isoformat()},
        "metrics": serialize(result.metrics),
        "rule_evaluation": serialize(ev.__dict__),
        "timeline": tl.to_list(),
        "assumptions": result.assumptions + [
            "交割日依 T+2 估算（尚未匯入證交所營業細則原文，屬待查證資訊）"],
        "warnings": serialize(warnings),
        "is_simulation": True,
    }
