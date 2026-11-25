"""融資交易（單一部位）計算。

官方公式來源：
- 擔保維持率＝（融資擔保品證券市值＋融券擔保品及保證金＋抵繳有價證券或其他商品市值）÷（融資金額＋融券標的證券市值）×100％
  （證券商辦理有價證券買賣融資融券業務操作辦法 第 53 條）。單一融資部位、無融券時化簡為 (M＋抵繳市值) ÷ D。
- 融資自備款差額＝融資金額－（計算日收盤價×融資股數×融資比率）－（抵繳市值×融資比率）（同辦法 第 54 條）。

限制：只支援「單一融資部位」。整戶維持率需要加總整戶資產與負債，見 portfolio.py；
本模組不處理除權息、停止買賣、無收盤價等特殊價格認定（第 53、54 條另有規定），結果會標示為簡化估算。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .fees import FeeSchedule, brokerage_fee, transaction_tax
from .interest import financing_interest
from .rounding import CALCULATION_VERSION, HUNDRED, ZERO, D, money, price, ratio_pct, safe_div
from .types import CalcWarning, Metric
from .validation import Validator


@dataclass
class MarginInput:
    buy_price: Decimal
    quantity: Decimal
    financing_ratio: Decimal
    current_price: Decimal
    maintenance_threshold: Decimal  # 小數，1.30 = 130%；由規則引擎提供
    cancel_threshold: Decimal | None = None  # 小數，1.66 = 166%；由規則引擎提供
    annual_interest_rate: Decimal | None = None
    holding_days: int = 0
    day_basis: int = 365
    fees: FeeSchedule = field(default_factory=FeeSchedule)
    sell_tax_rate: Decimal = D("0.003")
    other_collateral_value: Decimal = ZERO  # 抵繳有價證券市值（已依規定折算）
    financing_unit: Decimal = D("1")  # 融資金額計算單位（部分券商以千元為單位捨去，依契約設定）
    asset_label: str = "模擬資產"


@dataclass
class MarginResult:
    calculation_version: str
    metrics: dict[str, Metric]
    warnings: list[CalcWarning]
    assumptions: list[str]
    facts: dict[str, object]  # 給規則引擎用的事實


def _validate(i: MarginInput) -> None:
    v = Validator()
    v.positive("buy_price", i.buy_price, "買入價格")
    v.positive("quantity", i.quantity, "股數")
    v.integer("quantity", i.quantity, "股數")
    v.open_unit_interval("financing_ratio", i.financing_ratio, "融資比例")
    v.positive("current_price", i.current_price, "模擬目前價格")
    v.positive("maintenance_threshold", i.maintenance_threshold, "維持率門檻")
    v.rate("annual_interest_rate", i.annual_interest_rate, "融資年利率", D("0.5"))
    if i.holding_days < 0:
        v.add("holding_days", "must_be_non_negative", "持有天數不能是負數")
    if i.day_basis not in (360, 365):
        v.add("day_basis", "out_of_range", "年基準天數只支援 360 或 365")
    v.non_negative("other_collateral_value", i.other_collateral_value, "其他擔保品市值")
    v.rate("fee_rate", i.fees.fee_rate, "手續費率", D("0.01"))
    v.rate("fee_discount", i.fees.fee_discount, "手續費折扣")
    v.non_negative("min_fee", i.fees.min_fee, "最低手續費")
    v.rate("sell_tax_rate", i.sell_tax_rate, "交易稅率", D("0.01"))
    v.positive("financing_unit", i.financing_unit, "融資金額計算單位")
    v.raise_if_any()


def calculate_margin(i: MarginInput) -> MarginResult:
    _validate(i)
    warnings: list[CalcWarning] = []
    q = i.quantity
    purchase_value = money(i.buy_price * q)
    financing = (purchase_value * i.financing_ratio / i.financing_unit).to_integral_value(rounding="ROUND_DOWN") * i.financing_unit
    own_funds = purchase_value - financing
    buy_fee = brokerage_fee(purchase_value, i.fees)
    market_value = money(i.current_price * q)
    gross_pnl = market_value - purchase_value
    interest = financing_interest(financing, i.annual_interest_rate, i.holding_days, i.day_basis)
    if interest is None:
        warnings.append(CalcWarning("missing_interest_rate", "未輸入融資利率，淨損益未扣除利息"))
    sell_fee = brokerage_fee(market_value, i.fees)
    sell_tax = transaction_tax(market_value, i.sell_tax_rate)
    costs = buy_fee + sell_fee + sell_tax + (interest or ZERO)
    net_pnl = gross_pnl - costs

    equity_ret = safe_div(net_pnl, own_funds)
    ratio = safe_div(market_value + i.other_collateral_value, financing)
    ratio_pct_value = None if ratio is None else ratio_pct(ratio * HUNDRED)
    threshold_price = None
    cancel_price = None
    if financing > ZERO:
        threshold_price = max(ZERO, price((financing * i.maintenance_threshold - i.other_collateral_value) / q))
        if i.cancel_threshold is not None:
            cancel_price = max(ZERO, price((financing * i.cancel_threshold - i.other_collateral_value) / q))
    below = ratio is not None and ratio < i.maintenance_threshold
    call_amount = ZERO
    if below:
        # 第 54 條公式（官方以計算日收盤價計算；此處以模擬價格代入）
        call_amount = max(ZERO, money(financing - i.current_price * q * i.financing_ratio
                                      - i.other_collateral_value * i.financing_ratio))
    equity = market_value + i.other_collateral_value - financing
    if equity < ZERO:
        warnings.append(CalcWarning("negative_equity",
                                    "模擬市值已低於融資借款：即使全部賣出也不足清償，可能產生剩餘債務"))

    pct = lambda x: f"{ratio_pct(x * HUNDRED)}%"  # noqa: E731
    base = {"P0": str(i.buy_price), "Q": str(q), "F": pct(i.financing_ratio), "Pt": str(i.current_price)}
    m = {
        "purchase_value": Metric("purchase_value", "原始交易金額", purchase_value, "TWD", "P0 × Q",
                                 {"P0": base["P0"], "Q": base["Q"]}),
        "financing": Metric("financing", "融資借款", financing, "TWD", "P0 × Q × F（依融資金額計算單位捨去）",
                            {**base, "計算單位": str(i.financing_unit)}),
        "own_funds": Metric("own_funds", "自備本金", own_funds, "TWD", "原始交易金額 − 融資借款", {}),
        "cash_invested": Metric("cash_invested", "實際投入現金", own_funds + buy_fee, "TWD",
                                "自備本金 ＋ 買進手續費", {"買進手續費": str(buy_fee)}),
        "market_value": Metric("market_value", "模擬股票市值", market_value, "TWD", "Pt × Q",
                               {"Pt": base["Pt"], "Q": base["Q"]}),
        "gross_pnl": Metric("gross_pnl", "未計費用損益", gross_pnl, "TWD", "模擬市值 − 原始交易金額", {}),
        "buy_fee": Metric("buy_fee", "買進手續費", buy_fee, "TWD",
                          "max(最低手續費, 原始交易金額 × 費率 × 折扣)",
                          {"費率": str(i.fees.fee_rate), "折扣": str(i.fees.fee_discount), "最低": str(i.fees.min_fee)}),
        "sell_fee": Metric("sell_fee", "估計賣出手續費", sell_fee, "TWD",
                           "max(最低手續費, 模擬市值 × 費率 × 折扣)", {}, simplified=True,
                           note="假設以模擬價格全部賣出"),
        "sell_tax": Metric("sell_tax", "估計證券交易稅", sell_tax, "TWD", "模擬市值 × 稅率",
                           {"稅率": str(i.sell_tax_rate)}, ["TAX-GENERAL"], simplified=True),
        "interest": Metric("interest", "估計融資利息", interest, "TWD", "融資借款 × 年利率 × 持有天數 ÷ 年基準",
                           {"年利率": str(i.annual_interest_rate), "天數": str(i.holding_days),
                            "年基準": str(i.day_basis)}, simplified=True,
                           note="計息天數算法依券商契約"),
        "total_costs": Metric("total_costs", "估計交易成本合計", costs, "TWD",
                              "買進手續費 ＋ 賣出手續費 ＋ 交易稅 ＋ 利息", {}),
        "net_pnl": Metric("net_pnl", "模擬淨損益", net_pnl, "TWD", "未計費用損益 − 交易成本合計", {}, simplified=True),
        "equity_return": Metric("equity_return", "本金損益率",
                                None if equity_ret is None else ratio_pct(equity_ret * HUNDRED), "percent",
                                "模擬淨損益 ÷ 自備本金 × 100%", {}),
        "maintenance_ratio": Metric("maintenance_ratio", "擔保維持率（單一部位）", ratio_pct_value, "percent",
                                    "(模擬市值 ＋ 抵繳市值) ÷ 融資借款 × 100%",
                                    {"抵繳市值": str(i.other_collateral_value)}, ["MARGIN-RATIO-FORMULA"],
                                    simplified=True, note="官方以整戶計算；此處僅單一部位"),
        "threshold_price": Metric("threshold_price", "估計追繳門檻股價", threshold_price, "price",
                                  "(融資借款 × 門檻 − 抵繳市值) ÷ Q",
                                  {"門檻": pct(i.maintenance_threshold)}, ["MARGIN-CALL-THRESHOLD"],
                                  simplified=True, note="不是確定的斷頭價：處分還受通知送達、補繳期限、契約與成交狀況影響"),
        "cancel_price": Metric("cancel_price", "取消追繳紀錄所需股價", cancel_price, "price",
                               "(融資借款 × 取消門檻 − 抵繳市值) ÷ Q",
                               {"取消門檻": None if i.cancel_threshold is None else pct(i.cancel_threshold)},
                               ["MARGIN-CALL-CANCEL"], simplified=True),
        "margin_call_amount": Metric("margin_call_amount", "估計補繳差額", call_amount, "TWD",
                                     "融資借款 −（價格 × 股數 × 融資比率）−（抵繳市值 × 融資比率）",
                                     base, ["MARGIN-CALL-AMOUNT"], simplified=True,
                                     note="僅在維持率低於門檻時計算；實際以券商通知為準"),
        "equity": Metric("equity", "帳戶淨值（市值＋抵繳−借款）", equity, "TWD", "模擬市值 ＋ 抵繳市值 − 融資借款", {}),
    }
    assumptions = [
        f"資產：{i.asset_label}（模擬，非真實帳戶）",
        "僅計算單一融資部位，不含融券、其他信用部位與整戶合併",
        "以使用者輸入的模擬價格代替官方規定的計算日收盤價",
        f"手續費率 {i.fees.fee_rate}、折扣 {i.fees.fee_discount}、最低 {i.fees.min_fee} 元，無條件捨去到元（可調整）",
        f"融資利息以 {i.day_basis} 天為年基準、持有 {i.holding_days} 天估算",
    ]
    facts = {
        "trading_type": "margin",
        "maintenance_ratio": None if ratio is None else ratio,
        "equity": equity,
        "margin_call_amount": call_amount,
        "financing": financing,
        "market_value": market_value,
    }
    return MarginResult(CALCULATION_VERSION, m, warnings, assumptions, facts)


def ratio_curve(i: MarginInput, low: Decimal, high: Decimal, steps: int = 60) -> list[dict[str, str | None]]:
    """畫圖用：在價格區間內取樣，回傳 價格→維持率、本金損益、市值與負債。"""
    steps = max(2, min(steps, 400))
    out = []
    for n in range(steps + 1):
        p = price(low + (high - low) * Decimal(n) / Decimal(steps))
        if p <= ZERO:
            continue
        r = calculate_margin(MarginInput(**{**i.__dict__, "current_price": p}))
        out.append({
            "price": str(p),
            "maintenance_ratio": None if r.metrics["maintenance_ratio"].value is None
            else str(r.metrics["maintenance_ratio"].value),
            "gross_pnl": str(r.metrics["gross_pnl"].value),
            "net_pnl": str(r.metrics["net_pnl"].value),
            "market_value": str(r.metrics["market_value"].value),
            "financing": str(r.metrics["financing"].value),
        })
    return out
