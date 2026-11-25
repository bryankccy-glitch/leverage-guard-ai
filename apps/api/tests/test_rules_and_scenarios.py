from datetime import date
from decimal import Decimal as D

from app.legal_rules.engine import all_rule_versions, evaluate, select_rules
from app.scenario_engine.day_trade_scenario import DayTradeScenarioInput, run_day_trade_scenario, tax_rates
from app.scenario_engine.margin_scenario import MarginScenarioInput, Step, run_margin_scenario
from app.timeline_engine.trading_calendar import add_trading_days, is_trading_day


def test_every_sourced_rule_quotes_official_text():
    for rv in all_rule_versions():
        for c in rv.citations:
            assert c.validated, f"{rv.key} {c.article_number}: {c.validation_note}"


def test_rules_without_sources_are_flagged():
    unsourced = {rv.rule_id for rv in all_rule_versions() if not rv.raw.get("sources")}
    assert unsourced == {"DT-SETTLEMENT-CYCLE", "DT-FUNDING-GAP"}
    assert all(rv.is_demo for rv in all_rule_versions() if rv.rule_id in unsourced)


def test_threshold_rule_matching_and_missing_facts():
    e = evaluate("margin", {"maintenance_ratio": D("1.29")}, date(2026, 12, 1))
    assert "MARGIN-CALL-THRESHOLD" in e.matched
    e2 = evaluate("margin", {"maintenance_ratio": D("1.30")}, date(2026, 12, 1))
    assert "MARGIN-CALL-THRESHOLD" in e2.unmatched  # 「低於」130%，等於不觸發
    e3 = evaluate("margin", {}, date(2026, 12, 1))
    assert "maintenance_ratio" in e3.missing_facts["MARGIN-CALL-THRESHOLD"]
    assert e.unreviewed_rules  # 尚未人工審查的規則會被標示


def test_rule_version_selection_by_date():
    assert tax_rates(date(2026, 12, 1))["day_trade"] == D("0.0015")
    assert tax_rates(date(2027, 12, 31))["day_trade"] == D("0.0015")
    later = tax_rates(date(2028, 1, 3))
    assert later["day_trade"] == D("0.003") and later["note"]


def test_demo_rule_not_used_unless_requested():
    normal = select_rules("margin", date(2099, 6, 1))
    assert normal.rules["MARGIN-CALL-THRESHOLD"].version == "1.0.0"
    forced = select_rules("margin", date(2026, 12, 1), force_versions={"MARGIN-CALL-THRESHOLD": "9.0.0-demo"})
    assert forced.rules["MARGIN-CALL-THRESHOLD"].parameters["threshold"] == "1.40"


def test_conflicting_active_versions_are_not_auto_resolved():
    overrides = {"MARGIN-CALL-THRESHOLD@1.0.0": "active", "MARGIN-CALL-THRESHOLD@9.0.0-demo": "active"}
    sel = select_rules("margin", date(2099, 6, 1), include_demo=True, status_overrides=overrides)
    assert "MARGIN-CALL-THRESHOLD" not in sel.rules
    assert sel.conflicts and sel.conflicts[0]["rule_id"] == "MARGIN-CALL-THRESHOLD"


def test_trading_calendar():
    assert add_trading_days(date(2026, 12, 3), 2).date == date(2026, 12, 7)  # 週四 + 2 → 週一
    assert add_trading_days(date(2026, 12, 3), 2).coverage == "weekends_only"
    assert not is_trading_day(date(2027, 2, 2))  # 證交所公告：無交易僅辦理結算交割
    r = add_trading_days(date(2027, 2, 1), 1)
    assert r.date == date(2027, 2, 11) and r.coverage == "official"


DEMO_A = dict(buy_price=D("100"), quantity=D("1000"), financing_ratio=D("0.6"), start_date=date(2026, 12, 1),
              annual_interest_rate=D("0.0645"))


def test_demo_a_margin_call_disposal_remaining_debt():
    r = run_margin_scenario(MarginScenarioInput(**DEMO_A, steps=[
        Step(0, D("100")), Step(1, D("80")), Step(2, D("70")), Step(5, D("50"))]))
    events = [(n["event_type"], n["date"]) for n in r["timeline"]]
    assert ("maintenance_threshold_breach", "2026-12-03") in events
    assert ("top_up_deadline", "2026-12-07") in events
    assert ("collateral_disposal_condition", "2026-12-07") in events
    debt = next(n for n in r["timeline"] if n["event_type"] == "remaining_debt_notice")
    assert debt["financial_impact"]["可能的剩餘債務"] == "10295"
    assert all(b["validated"] for n in r["timeline"] for b in n["legal_basis"])


def test_demo_a_top_up_clears_call():
    r = run_margin_scenario(MarginScenarioInput(**DEMO_A, steps=[
        Step(0, D("100")), Step(2, D("70")), Step(3, D("70"), action="top_up", amount=D("18000"))]))
    types = [n["event_type"] for n in r["timeline"]]
    assert "margin_call_cleared" in types and "collateral_disposed" not in types


def test_unknown_notice_date_does_not_invent_deadline():
    r = run_margin_scenario(MarginScenarioInput(**DEMO_A, notice_served="unknown",
                                                steps=[Step(0, D("100")), Step(2, D("70")), Step(6, D("50"))]))
    notice = next(n for n in r["timeline"] if n["event_type"] == "margin_call_notice")
    assert notice["status"] == "requires_confirmation" and notice["date"] is None
    assert "top_up_deadline" not in [n["event_type"] for n in r["timeline"]]


def test_rule_change_demo_changes_events():
    steps = [Step(0, D("100")), Step(1, D("82"))]  # 82,000/60,000 = 136.67%
    old = run_margin_scenario(MarginScenarioInput(**DEMO_A, steps=steps))
    new = run_margin_scenario(MarginScenarioInput(**DEMO_A, steps=steps,
                                                  rule_overrides={"MARGIN-CALL-THRESHOLD": "9.0.0-demo"}))
    assert "maintenance_threshold_breach" not in [n["event_type"] for n in old["timeline"]]
    assert "maintenance_threshold_breach" in [n["event_type"] for n in new["timeline"]]
    assert old["rule_version"] != new["rule_version"]


def test_demo_b_partial_day_trade():
    r = run_day_trade_scenario(DayTradeScenarioInput("buy_first", D("100"), D("2000"), D("102"), D("1000"),
                                                     date(2026, 12, 1), available_cash=D("50000")))
    types = {n["event_type"]: n for n in r["timeline"]}
    assert "normal_settlement_obligation" in types
    assert types["funding_gap_estimated"]["status"] == "requires_confirmation"
    assert types["settlement_due"]["unverified"] is True
    assert r["parameters"]["settlement_date"] == "2026-12-03"


def test_sell_first_unmatched_timeline():
    r = run_day_trade_scenario(DayTradeScenarioInput("sell_first", D("100"), D("500"), D("102"), D("1000"),
                                                     date(2026, 12, 3), assumed_buyback_price=D("104"),
                                                     assumed_borrow_fee_rate=D("0.02")))
    t = {n["event_type"]: n for n in r["timeline"]}
    assert t["forced_buy_in"]["date"] == "2026-12-04"
    assert t["buyin_cost_due"]["deadline"] == "2026-12-07"
