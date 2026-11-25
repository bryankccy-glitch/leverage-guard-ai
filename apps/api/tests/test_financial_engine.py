"""金融計算引擎：人工驗算的 Golden Cases、邊界條件與性質測試。

每個 golden case 的期望值都在註解裡附上手算過程。
"""
from decimal import Decimal as D

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.financial_engine.day_trading import DayTradeInput, calculate_day_trade
from app.financial_engine.fees import FeeSchedule, brokerage_fee, transaction_tax
from app.financial_engine.interest import financing_interest
from app.financial_engine.liquidation import DisposalInput, simulate_disposal
from app.financial_engine.margin import MarginInput, calculate_margin
from app.financial_engine.portfolio import PositionLine, account_ratio
from app.financial_engine.rounding import D as toD
from app.financial_engine.validation import CalculationInputError


def margin(**kw):
    base = dict(buy_price=D("100"), quantity=D("1000"), financing_ratio=D("0.6"), current_price=D("100"),
                maintenance_threshold=D("1.30"), cancel_threshold=D("1.66"))
    base.update(kw)
    return calculate_margin(MarginInput(**base))


def v(res, key):
    return res.metrics[key].value


# ───── Golden cases（示範情境 A）─────

def test_golden_margin_opening():
    # 100 × 1000 = 100,000；融資 60% = 60,000；自備 40,000；維持率 100,000/60,000 = 166.67%
    r = margin()
    assert v(r, "purchase_value") == D("100000")
    assert v(r, "financing") == D("60000")
    assert v(r, "own_funds") == D("40000")
    assert v(r, "maintenance_ratio") == D("166.67")
    # 門檻股價 = 60,000 × 1.30 / 1000 = 78.00；取消股價 = 60,000 × 1.66 / 1000 = 99.60
    assert v(r, "threshold_price") == D("78.00")
    assert v(r, "cancel_price") == D("99.60")
    # 買進手續費 = 100,000 × 0.001425 = 142.5 → 無條件捨去 142
    assert v(r, "buy_fee") == D("142")


@pytest.mark.parametrize("price, ratio, gross, below", [
    ("80", "133.33", "-20000", False),  # 80,000/60,000
    ("70", "116.67", "-30000", True),   # 70,000/60,000
    ("50", "83.33", "-50000", True),    # 50,000/60,000
])
def test_golden_margin_price_drops(price, ratio, gross, below):
    r = margin(current_price=D(price))
    assert v(r, "maintenance_ratio") == D(ratio)
    assert v(r, "gross_pnl") == D(gross)
    assert (v(r, "margin_call_amount") > 0) == below


def test_golden_margin_call_amount_article_54():
    # 第 54 條：60,000 − 70 × 1000 × 0.6 = 18,000
    assert v(margin(current_price=D("70")), "margin_call_amount") == D("18000")
    # 價格 70、抵繳 10,000：維持率 80,000/60,000 = 133.33% → 不追繳
    assert v(margin(current_price=D("70"), other_collateral_value=D("10000")), "margin_call_amount") == D("0")
    # 價格 60、抵繳 10,000：維持率 116.67%；差額 60,000 − 36,000 − 10,000 × 0.6 = 18,000
    assert v(margin(current_price=D("60"), other_collateral_value=D("10000")), "margin_call_amount") == D("18000")


def test_golden_equity_and_costs_at_50():
    # 市值 50,000；賣出手續費 71（71.25 捨去）；交易稅 150；買進手續費 142；無利息
    r = margin(current_price=D("50"))
    assert v(r, "sell_fee") == D("71")
    assert v(r, "sell_tax") == D("150")
    assert v(r, "net_pnl") == D("-50000") - D("142") - D("71") - D("150")
    assert v(r, "equity") == D("-10000")
    assert any(w.code == "negative_equity" for w in r.warnings)
    # 本金損益率 = −50,363 / 40,000 = −125.91%
    assert v(r, "equity_return") == D("-125.91")


def test_interest():
    # 60,000 × 6.45% × 7 / 365 = 74.21 → 74
    assert financing_interest(D("60000"), D("0.0645"), 7) == D("74")
    assert financing_interest(D("60000"), None, 7) is None
    assert financing_interest(D("60000"), D("0.0645"), 0) == D("0")
    assert margin().warnings[0].code == "missing_interest_rate"


def test_fees_and_tax():
    s = FeeSchedule()
    assert brokerage_fee(D("1000"), s) == D("20")  # 1.425 → 最低 20
    assert brokerage_fee(D("0"), s) == D("0")
    assert brokerage_fee(D("100000"), FeeSchedule(fee_discount=D("0.28"))) == D("39")  # 39.9 捨去
    assert transaction_tax(D("102000"), D("0.0015")) == D("153")


def test_disposal_remaining_debt_and_surplus():
    # 處分 50 元：50,000 − 71 − 150 = 49,779；債務 60,074 → 剩餘 10,295
    r = simulate_disposal(DisposalInput(quantity=D("1000"), disposal_price=D("50"), outstanding_debt=D("60000"),
                                        accrued_interest=D("74")))
    assert r["net_proceeds"].value == D("49779")
    assert r["remaining_debt"].value == D("10295")
    assert r["surplus_returned"].value == D("0")
    # 處分 75 元：75,000 − 106 − 225 = 74,669 → 溢額 14,669
    r2 = simulate_disposal(DisposalInput(quantity=D("1000"), disposal_price=D("75"), outstanding_debt=D("60000")))
    assert r2["surplus_returned"].value == D("14669")
    assert r2["remaining_debt"].value == D("0")
    # 流動性不足：只成交 400 股
    r3 = simulate_disposal(DisposalInput(quantity=D("1000"), disposal_price=D("50"), outstanding_debt=D("60000"),
                                         filled_quantity=D("400")))
    assert r3["unfilled_quantity"].value == D("600")


def test_portfolio_ratio_is_not_average():
    # A：市值 100,000／借 60,000（166.67%）；B：市值 30,000／借 30,000（100%）
    # 整戶 = 130,000 / 90,000 = 144.44%，不是兩者平均 133.33%
    r = account_ratio([PositionLine("A", D("1000"), D("100"), D("60000")),
                       PositionLine("B", D("1000"), D("30"), D("30000"))])
    assert r["account_maintenance_ratio"].value == D("144.44")


# ───── 當沖 Golden cases（示範情境 B）─────

def dt(**kw):
    base = dict(direction="buy_first", buy_price=D("100"), buy_quantity=D("1000"), sell_price=D("102"),
                sell_quantity=D("1000"), day_trade_tax_rate=D("0.0015"), general_tax_rate=D("0.003"))
    base.update(kw)
    return calculate_day_trade(DayTradeInput(**base))


def test_golden_day_trade_complete():
    # 毛利 2,000；手續費 142 + 145 = 287；稅 102,000 × 0.0015 = 153；淨 1,560
    r = dt()
    assert v(r, "gross_pnl") == D("2000")
    assert v(r, "fees") == D("287")
    assert v(r, "tax_day_trade") == D("153")
    assert v(r, "net_pnl") == D("1560")
    assert v(r, "unmatched_long") == 0 and v(r, "unmatched_short") == 0
    assert v(r, "settlement_payable") == D("-1560")  # 應收


def test_golden_day_trade_partial():
    # 買 2000、賣 1000：未沖銷 1000 股須全額交割
    # 買進手續費 285（285 整）；分攤到已沖銷 142.5→143、未沖銷 143
    # 已沖銷淨損益 = 2000 − (143 + 145) − 153 = 1,559
    # 交割應付 = 100,000 + 143 − 1,559 = 98,584；可用 50,000 → 缺口 48,584
    r = dt(buy_quantity=D("2000"), available_cash=D("50000"))
    assert v(r, "net_pnl") == D("1559")
    assert v(r, "settlement_payable") == D("98584")
    assert v(r, "funding_gap") == D("48584")
    assert any(w.code == "funding_gap" for w in r.warnings)


def test_day_trade_sell_first_unmatched_uses_general_tax():
    # 賣 2000、買 1000：未買回 1000 股的賣出適用千分之三
    r = dt(direction="sell_first", buy_quantity=D("1000"), sell_quantity=D("2000"))
    assert v(r, "unmatched_short") == D("1000")
    assert v(r, "tax_general") == D("306")  # 102,000 × 0.003
    assert v(r, "estimated_buyback_cost") is None
    r2 = dt(direction="sell_first", buy_quantity=D("1000"), sell_quantity=D("2000"),
            assumed_buyback_price=D("105"), assumed_borrow_fee_rate=D("0.01"))
    # 105,000 + 手續費 149 + 借券費 1,050 = 106,199
    assert v(r2, "estimated_buyback_cost") == D("106199")


# ───── 驗證與邊界 ─────

@pytest.mark.parametrize("kw, field", [
    ({"financing_ratio": D("0")}, "financing_ratio"),
    ({"financing_ratio": D("1")}, "financing_ratio"),
    ({"quantity": D("-1")}, "quantity"),
    ({"quantity": D("10.5")}, "quantity"),
    ({"buy_price": D("0")}, "buy_price"),
    ({"current_price": D("-5")}, "current_price"),
    ({"annual_interest_rate": D("2")}, "annual_interest_rate"),
])
def test_margin_rejects_invalid(kw, field):
    with pytest.raises(CalculationInputError) as e:
        margin(**kw)
    assert any(err.field == field for err in e.value.errors)


def test_day_trade_rejects_invalid():
    with pytest.raises(CalculationInputError):
        dt(direction="sideways")
    with pytest.raises(CalculationInputError):
        dt(buy_quantity=D("0"), sell_quantity=D("0"))


def test_decimal_rejects_float():
    with pytest.raises(TypeError):
        toD(0.1)
    with pytest.raises(ValueError):
        toD("abc")
    with pytest.raises(ValueError):
        toD("NaN")


# ───── 性質測試 ─────

prices = st.decimals(min_value=D("0.01"), max_value=D("5000"), places=2, allow_nan=False, allow_infinity=False)
qty = st.integers(min_value=1, max_value=1_000_000).map(D)
ratio = st.decimals(min_value=D("0.01"), max_value=D("0.99"), places=2)


@settings(max_examples=200, deadline=None)
@given(p0=prices, q=qty, f=ratio, p1=prices, p2=prices)
def test_property_ratio_monotonic_and_finite(p0, q, f, p1, p2):
    lo, hi = sorted([p1, p2])
    a = margin(buy_price=p0, quantity=q, financing_ratio=f, current_price=lo)
    b = margin(buy_price=p0, quantity=q, financing_ratio=f, current_price=hi)
    for r in (a, b):
        for m in r.metrics.values():
            assert m.value is None or m.value.is_finite()
        assert v(r, "sell_fee") >= 0 and v(r, "sell_tax") >= 0 and v(r, "buy_fee") >= 0
    ra, rb = v(a, "maintenance_ratio"), v(b, "maintenance_ratio")
    if ra is not None and rb is not None:
        assert ra <= rb  # 負債固定時，市值下降不會讓維持率上升


@settings(max_examples=100, deadline=None)
@given(p0=prices, q=qty, f=ratio, p=prices)
def test_property_deterministic(p0, q, f, p):
    a = margin(buy_price=p0, quantity=q, financing_ratio=f, current_price=p)
    b = margin(buy_price=p0, quantity=q, financing_ratio=f, current_price=p)
    assert {k: m.value for k, m in a.metrics.items()} == {k: m.value for k, m in b.metrics.items()}


@settings(max_examples=150, deadline=None)
@given(bp=prices, sp=prices, bq=st.integers(0, 100_000), sq=st.integers(0, 100_000), cash=prices)
def test_property_day_trade_quantities(bp, sp, bq, sq, cash):
    if bq == 0 and sq == 0:
        return
    direction = "buy_first" if bq > 0 else "sell_first"
    r = dt(direction=direction, buy_price=bp, sell_price=sp, buy_quantity=D(bq), sell_quantity=D(sq),
           available_cash=cash)
    assert v(r, "matched_quantity") + v(r, "unmatched_long") == D(bq)
    assert v(r, "matched_quantity") + v(r, "unmatched_short") == D(sq)
    assert v(r, "funding_gap") >= 0
