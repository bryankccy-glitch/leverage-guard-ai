"""融資多步驟情境推演：每一步重算財務狀態，再由規則引擎判斷法律事件，產生時間軸。

假設（都會寫進結果的 assumptions）：
- 「通知送達日」由使用者選：跌破當日送達、次一營業日送達，或未知（未知時不計算期限，事件標為 requires_confirmation）。
- 補繳現金視為償還部分融資（降低融資金額）；抵繳品依使用者輸入的折算後市值計入。
- 處分以「可處分首日之後第一個情境步驟」的模擬價格成交；可設定連續未成交天數模擬流動性不足。
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal
from typing import Any

from ..financial_engine.fees import FeeSchedule
from ..financial_engine.interest import financing_interest
from ..financial_engine.liquidation import DisposalInput, simulate_disposal
from ..financial_engine.margin import MarginInput, calculate_margin
from ..financial_engine.rounding import ZERO, D, money
from ..financial_engine.types import serialize
from ..legal_rules.engine import evaluate, param, rule_version_label, select_rules
from ..timeline_engine.builder import TimelineBuilder
from ..timeline_engine.trading_calendar import add_trading_days, next_trading_day


@dataclass
class Step:
    day: int  # 距離建倉日的交易日數
    price: Decimal
    label: str = ""
    action: str = "none"  # none | top_up | add_collateral | repay
    amount: Decimal = ZERO


@dataclass
class MarginScenarioInput:
    buy_price: Decimal
    quantity: Decimal
    financing_ratio: Decimal
    start_date: date
    steps: list[Step]
    annual_interest_rate: Decimal | None = None
    fees: FeeSchedule = field(default_factory=FeeSchedule)
    notice_served: str = "same_day"  # same_day | next_trading_day | unknown
    unfilled_disposal_days: int = 0  # 流動性不足：連續未能全數成交的營業日數
    disposal_fill_ratio: Decimal = D("1")
    other_collateral_value: Decimal = ZERO
    asset_label: str = "模擬資產"
    rule_overrides: dict[str, str] | None = None  # 規則版本比較用
    include_demo_rules: bool = False
    status_overrides: dict[str, str] | None = None


def run_margin_scenario(s: MarginScenarioInput) -> dict[str, Any]:
    if not s.steps:
        raise ValueError("情境至少需要一個步驟")
    steps = sorted(s.steps, key=lambda x: x.day)
    if steps[0].day < 0:
        raise ValueError("步驟的交易日數不能是負數")
    sel = select_rules("margin", s.start_date, include_demo=s.include_demo_rules,
                       status_overrides=s.status_overrides, force_versions=s.rule_overrides)
    threshold = param(sel.rules, "MARGIN-CALL-THRESHOLD", "threshold")
    cancel = param(sel.rules, "MARGIN-CALL-CANCEL", "cancel_threshold")
    deadline_days = param(sel.rules, "MARGIN-CALL-DEADLINE", "business_days")
    tax_rate = param(select_rules("general", s.start_date, status_overrides=s.status_overrides).rules,
                     "TAX-GENERAL", "rate") or D("0.003")
    if threshold is None:
        raise ValueError("沒有生效的維持率門檻規則，無法推演（需要人工確認規則）")

    tl = TimelineBuilder({**sel.rules, **select_rules("general", s.start_date,
                                                      status_overrides=s.status_overrides).rules})
    assumptions = {
        "same_day": "假設追繳通知於維持率跌破當日送達",
        "next_trading_day": "假設追繳通知於跌破後次一營業日送達",
        "unknown": "通知送達日未知：不計算補繳期限",
    }
    assumption_list = [assumptions[s.notice_served],
                       "補繳現金視為償還部分融資", "處分以模擬價格成交，實際成交價可能不同",
                       "未計入除權息、停止買賣等特殊價格認定"]

    base = MarginInput(buy_price=s.buy_price, quantity=s.quantity, financing_ratio=s.financing_ratio,
                       current_price=s.buy_price, maintenance_threshold=threshold, cancel_threshold=cancel,
                       annual_interest_rate=s.annual_interest_rate, fees=s.fees, sell_tax_rate=tax_rate,
                       other_collateral_value=s.other_collateral_value, asset_label=s.asset_label)
    opening = calculate_margin(base)
    financing = opening.metrics["financing"].value
    collateral = s.other_collateral_value
    tl.add(0, s.start_date, "position_opened", "triggered_in_simulation", "使用者建立模擬融資部位",
           ["MARGIN-CONTRACT-REQUIRED"], {"融資借款": financing, "自備本金": opening.metrics["own_funds"].value})

    states = []
    in_call = False
    call_amount = ZERO
    topped_up = ZERO
    notice_date: date | None = None
    deadline: date | None = None
    deadline_note = None
    disposal_from: date | None = None
    disposed = False
    disposal_result = None
    for idx, st in enumerate(steps, start=1):
        d = add_trading_days(s.start_date, st.day).date
        if disposed:
            break
        # 使用者動作
        if st.action == "top_up" and st.amount > ZERO:
            topped_up += st.amount
            financing = max(ZERO, financing - st.amount)
            tl.add(idx, d, "top_up_paid", "triggered_in_simulation", f"使用者補繳 {st.amount} 元",
                   ["MARGIN-CALL-CANCEL"], {"補繳金額": st.amount, "補繳後融資金額": financing})
        elif st.action == "repay" and st.amount > ZERO:
            financing = max(ZERO, financing - st.amount)
        elif st.action == "add_collateral" and st.amount > ZERO:
            collateral += st.amount
        holding_days = (d - s.start_date).days
        r = calculate_margin(replace(base, current_price=st.price, other_collateral_value=collateral,
                                     holding_days=holding_days))
        # 融資金額可能因補繳／還款而改變：以目前融資金額重算維持率
        mv = r.metrics["market_value"].value
        ratio = None if financing == ZERO else (mv + collateral) / financing
        ratio_pct = None if ratio is None else (ratio * 100).quantize(D("0.01"))
        tl.add(idx, d, "price_change", "triggered_in_simulation",
               f"模擬價格 {st.price}" + (f"（{st.label}）" if st.label else ""), [],
               {"模擬市值": mv, "擔保維持率%": ratio_pct, "未計費用損益": r.metrics["gross_pnl"].value})
        facts: dict[str, Any] = {"maintenance_ratio": ratio}

        if not in_call and ratio is not None and ratio < threshold:
            in_call = True
            call_amount = max(ZERO, money(financing - st.price * s.quantity * s.financing_ratio
                                          - collateral * s.financing_ratio))
            topped_up = ZERO
            tl.add(idx, d, "maintenance_threshold_breach", "triggered_in_simulation",
                   f"維持率 {ratio_pct}% 低於門檻 {threshold * 100}%", ["MARGIN-CALL-THRESHOLD", "MARGIN-RATIO-FORMULA"],
                   {"擔保維持率%": ratio_pct, "估計補繳差額": call_amount})
            if s.notice_served == "unknown":
                tl.add(idx, None, "margin_call_notice", "requires_confirmation", "券商通知送達日未知",
                       ["MARGIN-CALL-THRESHOLD"], uncertainty=["沒有通知送達日，無法計算補繳期限"])
            else:
                notice_date = d if s.notice_served == "same_day" else next_trading_day(d).date
                cal = add_trading_days(notice_date, int(deadline_days or 2))
                deadline, deadline_note = cal.date, cal.note
                tl.add(idx, notice_date, "margin_call_notice", "triggered_in_simulation",
                       "模擬券商發出補繳通知（不是真實券商通知）", ["MARGIN-CALL-THRESHOLD"],
                       {"估計補繳差額": call_amount}, uncertainty=[assumptions[s.notice_served]])
                tl.add(idx, deadline, "top_up_deadline", "potential",
                       f"自通知送達日起 {deadline_days} 個營業日", ["MARGIN-CALL-DEADLINE", "MARGIN-CALL-AMOUNT"],
                       {"估計補繳差額": call_amount}, deadline=deadline, deadline_note=deadline_note)

        if in_call:
            facts.update({"topped_up_amount": topped_up, "margin_call_amount": call_amount})
            ev = evaluate("margin", facts, d, include_demo=s.include_demo_rules,
                          status_overrides=s.status_overrides, force_versions=s.rule_overrides)
            if "margin_call_cleared" in ev.triggered_events:
                in_call = False
                tl.add(idx, d, "margin_call_cleared", "resolved",
                       "維持率回升至取消門檻以上，或補繳達通知差額", ["MARGIN-CALL-CANCEL"], {"擔保維持率%": ratio_pct})
                deadline = None
            elif deadline is not None and d > deadline and disposal_from is None:
                passed = {"deadline_passed": True, "margin_call_cleared": False, "maintenance_ratio": ratio}
                ev2 = evaluate("margin", passed, d, include_demo=s.include_demo_rules,
                               status_overrides=s.status_overrides, force_versions=s.rule_overrides)
                if "collateral_disposal_condition" in ev2.triggered_events:
                    disposal_from = next_trading_day(deadline).date
                    tl.add(idx, deadline, "collateral_disposal_condition", "triggered_in_simulation",
                           "期限屆滿仍未補足，且維持率仍低於門檻（以本步驟模擬價格判斷）",
                           ["MARGIN-DISPOSAL-CONDITION"], deadline=disposal_from,
                           deadline_note="自次一營業日起處分",
                           uncertainty=["情境步驟之間的每日價格未知，以下一個步驟的價格代表期限當日價格"])
                elif "disposal_deferred" in ev2.triggered_events:
                    tl.add(idx, deadline, "disposal_deferred", "potential", "期限當日維持率回升至門檻以上",
                           ["MARGIN-DISPOSAL-DEFERRED"])
                    deadline = None
            if disposal_from is not None and d >= disposal_from and not disposed:
                disposed = True
                interest = financing_interest(financing, s.annual_interest_rate, holding_days) or ZERO
                fill = s.disposal_fill_ratio if s.unfilled_disposal_days >= 6 else D("1")
                filled_qty = (s.quantity * fill).to_integral_value(rounding="ROUND_DOWN")
                disp = simulate_disposal(DisposalInput(quantity=s.quantity, disposal_price=st.price,
                                                       outstanding_debt=financing, accrued_interest=interest,
                                                       fees=s.fees, sell_tax_rate=tax_rate,
                                                       filled_quantity=filled_qty))
                tl.add(idx, d, "collateral_disposed", "triggered_in_simulation",
                       f"以模擬價格 {st.price} 處分擔保品", ["MARGIN-DISPOSAL-CONDITION"],
                       {"處分淨所得": disp["net_proceeds"].value, "應清償債務": disp["total_debt"].value})
                if s.unfilled_disposal_days >= 6:
                    tl.add(idx, d, "disposal_unfilled", "triggered_in_simulation",
                           f"模擬連續 {s.unfilled_disposal_days} 個營業日無法全數成交", ["MARGIN-LIQUIDITY-FAILURE"],
                           {"未成交股數": disp["unfilled_quantity"].value})
                rem = disp["remaining_debt"].value
                ev3 = evaluate("margin", {"remaining_debt": rem, "surplus_returned": disp["surplus_returned"].value},
                               d, status_overrides=s.status_overrides)
                if "remaining_debt_notice" in ev3.triggered_events:
                    due = next_trading_day(d)
                    tl.add(idx, d, "remaining_debt_notice", "triggered_in_simulation",
                           "處分所得不足清償債務", ["MARGIN-DISPOSAL-SHORTFALL"], {"可能的剩餘債務": rem},
                           deadline=due.date, deadline_note=due.note)
                    tl.add(idx, None, "default_report", "requires_confirmation",
                           "若補足通知與限期清償後仍未清償", ["MARGIN-DEFAULT-REPORT", "MARGIN-PENALTY"],
                           uncertainty=["是否申報違約取決於券商實際通知與清償情形"])
                if "surplus_returned" in ev3.triggered_events:
                    tl.add(idx, d, "surplus_returned", "triggered_in_simulation", "處分所得清償後仍有剩餘",
                           ["MARGIN-DISPOSAL-SURPLUS"], {"應發還溢額": disp["surplus_returned"].value})
                disposal_result = serialize(disp)
        states.append({"step": idx, "date": d.isoformat(), "label": st.label, "price": str(st.price),
                       "financing": str(financing), "collateral": str(collateral),
                       "maintenance_ratio_pct": None if ratio_pct is None else str(ratio_pct),
                       "in_margin_call": in_call, "metrics": serialize(r.metrics),
                       "disposal": disposal_result if disposed and disposal_result and
                       not any(x.get("disposal") for x in states) else None})

    tl.add(len(steps) + 1, None, "dispute_available", "potential", "對通知、處分或結算有疑義時", ["GENERAL-DISPUTE"])
    return {
        "trading_type": "margin",
        "calculation_version": opening.calculation_version,
        "rule_version": rule_version_label(sel.rules),
        "rule_versions": {k: v.version for k, v in sel.rules.items()},
        "rule_conflicts": sel.conflicts,
        "parameters": {"maintenance_threshold": str(threshold), "cancel_threshold": str(cancel),
                       "deadline_business_days": str(deadline_days)},
        "opening": serialize(opening.metrics),
        "states": states,
        "timeline": tl.to_list(),
        "assumptions": assumption_list + opening.assumptions,
        "warnings": serialize(opening.warnings),
        "is_simulation": True,
    }
