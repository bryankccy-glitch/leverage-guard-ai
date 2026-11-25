"""把 API 輸入轉成引擎輸入；計算本身全部交給 financial_engine / scenario_engine。"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from ..financial_engine.fees import FeeSchedule
from ..financial_engine.margin import MarginInput, calculate_margin, ratio_curve
from ..financial_engine.portfolio import PositionLine, account_ratio
from ..financial_engine.rounding import ZERO
from ..financial_engine.types import serialize
from ..legal_rules.engine import evaluate, legal_corpus, param, rule_version_label, select_rules
from ..scenario_engine.day_trade_scenario import DayTradeScenarioInput, run_day_trade_scenario
from ..scenario_engine.margin_scenario import MarginScenarioInput, Step, run_margin_scenario
from ..schemas.calc import DayTradeCalcIn, MarginCalcIn, MarginScenarioIn, PortfolioCalcIn, dec


def fees(f: Any) -> FeeSchedule:
    d = f.dec()
    return FeeSchedule(fee_rate=d["fee_rate"], fee_discount=d["fee_discount"], min_fee=d["min_fee"])


def legal_source_version() -> str:
    docs = legal_corpus()
    return ";".join(f"{k}@{v['version']}" for k, v in sorted(docs.items()))


def margin_calc(body: MarginCalcIn, status_overrides: dict[str, str] | None = None) -> dict[str, Any]:
    as_of = body.as_of or date.today()
    sel = select_rules("margin", as_of, status_overrides=status_overrides)
    gen = select_rules("general", as_of, status_overrides=status_overrides)
    threshold = param(sel.rules, "MARGIN-CALL-THRESHOLD", "threshold")
    if threshold is None:
        from ..core.errors import ApiError
        raise ApiError(409, "conflict", "目前沒有可用的維持率門檻規則（可能有衝突待人工確認）",
                       {"conflicts": sel.conflicts})
    inp = MarginInput(
        buy_price=dec(body.buy_price), quantity=dec(body.quantity), financing_ratio=dec(body.financing_ratio),
        current_price=dec(body.current_price), maintenance_threshold=threshold,
        cancel_threshold=param(sel.rules, "MARGIN-CALL-CANCEL", "cancel_threshold"),
        annual_interest_rate=dec(body.annual_interest_rate), holding_days=body.holding_days,
        day_basis=body.day_basis, fees=fees(body.fees),
        sell_tax_rate=param(gen.rules, "TAX-GENERAL", "rate") or Decimal("0.003"),
        other_collateral_value=dec(body.other_collateral_value) or ZERO, asset_label=body.asset_label)
    r = calculate_margin(inp)
    ev = evaluate("margin", r.facts, as_of, status_overrides=status_overrides)
    curve = None
    if body.curve:
        lo = max(Decimal("0.01"), inp.buy_price * Decimal("0.3"))
        curve = ratio_curve(inp, lo, inp.buy_price * Decimal("1.3"), 60)
    rules_used = {**sel.rules, **gen.rules}
    return {
        "calculation_version": r.calculation_version,
        "rule_version": rule_version_label(rules_used),
        "legal_source_version": legal_source_version(),
        "as_of": as_of.isoformat(),
        "metrics": serialize(r.metrics),
        "warnings": serialize(r.warnings),
        "assumptions": r.assumptions,
        "rule_evaluation": serialize(ev.__dict__),
        "rules": rules_summary(rules_used),
        "curve": curve,
        "is_simulation": True,
        "is_simplified": True,
    }


def rules_summary(rules: dict) -> list[dict[str, Any]]:
    out = []
    for rid, rv in rules.items():
        out.append({
            "rule_id": rid, "version": rv.version, "rule_name": rv.rule_name, "review_status": rv.review_status,
            "is_demo": rv.is_demo, "plain_language": rv.plain_language, "parameters": rv.parameters,
            "citation_validated": rv.citation_ok, "has_official_source": bool(rv.raw.get("sources")),
            "citations": [c.__dict__ for c in rv.citations],
        })
    return out


def day_trade_calc(body: DayTradeCalcIn, status_overrides: dict[str, str] | None = None) -> dict[str, Any]:
    out = run_day_trade_scenario(DayTradeScenarioInput(
        direction=body.direction, buy_price=dec(body.buy_price), buy_quantity=dec(body.buy_quantity),
        sell_price=dec(body.sell_price), sell_quantity=dec(body.sell_quantity), trade_date=body.trade_date,
        available_cash=dec(body.available_cash) or ZERO, fees=fees(body.fees),
        assumed_buyback_price=dec(body.assumed_buyback_price),
        assumed_borrow_fee_rate=dec(body.assumed_borrow_fee_rate), asset_label=body.asset_label,
        status_overrides=status_overrides))
    sel = select_rules("day_trading", body.trade_date, status_overrides=status_overrides)
    out["rules"] = rules_summary(sel.rules)
    out["legal_source_version"] = legal_source_version()
    return out


def margin_scenario(body: MarginScenarioIn, status_overrides: dict[str, str] | None = None,
                    include_demo: bool = False) -> dict[str, Any]:
    out = run_margin_scenario(MarginScenarioInput(
        buy_price=dec(body.buy_price), quantity=dec(body.quantity), financing_ratio=dec(body.financing_ratio),
        start_date=body.start_date,
        steps=[Step(s.day, dec(s.price), s.label, s.action, dec(s.amount) or ZERO) for s in body.steps],
        annual_interest_rate=dec(body.annual_interest_rate), fees=fees(body.fees), notice_served=body.notice_served,
        unfilled_disposal_days=body.unfilled_disposal_days, disposal_fill_ratio=dec(body.disposal_fill_ratio),
        other_collateral_value=dec(body.other_collateral_value) or ZERO, asset_label=body.asset_label,
        rule_overrides=body.rule_overrides, include_demo_rules=include_demo or bool(body.rule_overrides),
        status_overrides=status_overrides))
    sel = select_rules("margin", body.start_date, status_overrides=status_overrides,
                       force_versions=body.rule_overrides, include_demo=bool(body.rule_overrides))
    out["rules"] = rules_summary(sel.rules)
    out["legal_source_version"] = legal_source_version()
    return out


def portfolio_calc(body: PortfolioCalcIn) -> dict[str, Any]:
    m = account_ratio([PositionLine(p.label, dec(p.quantity), dec(p.simulated_price), dec(p.financing_principal))
                       for p in body.positions], dec(body.collateral_value) or ZERO)
    return {"metrics": serialize(m), "is_simulation": True,
            "limitations": ["只計算融資部位與抵繳品，不含融券", "以模擬價格代替收盤價"]}
