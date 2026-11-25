"""極端情境實驗室的 12 個預設情境。全部是虛構的模擬參數，不是市場預測。"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def _start() -> str:
    d = date.today()
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.isoformat()


BASE_MARGIN = {"asset_label": "示範股票（虛構）", "buy_price": "100", "quantity": "1000", "financing_ratio": "0.6",
               "annual_interest_rate": "0.0645"}
BASE_DT = {"asset_label": "示範股票（虛構）", "buy_price": "100", "sell_price": "98", "buy_quantity": "2000",
           "sell_quantity": "2000", "available_cash": "50000"}


def presets() -> list[dict[str, Any]]:
    s = _start()

    def m(key, zh, en, steps, **extra):
        return {"key": key, "title_zh": zh, "title_en": en, "trading_type": "margin",
                "input": {**BASE_MARGIN, "start_date": s, "steps": steps, **extra}}

    def d(key, zh, en, **extra):
        return {"key": key, "title_zh": zh, "title_en": en, "trading_type": "day_trading",
                "input": {**BASE_DT, "trade_date": s, **extra}}

    return [
        m("drop5", "股價下跌 5%", "Price falls 5%", [{"day": 0, "price": "100"}, {"day": 1, "price": "95"}]),
        m("drop10", "股價下跌 10%", "Price falls 10%", [{"day": 0, "price": "100"}, {"day": 1, "price": "90"}]),
        m("drop20", "股價下跌 20%", "Price falls 20%",
          [{"day": 0, "price": "100"}, {"day": 1, "price": "80"}, {"day": 4, "price": "80"}]),
        m("multi_day", "連續數日下跌（自訂跌幅，非真實漲跌幅限制）", "Consecutive declines (assumed, not real price limits)",
          [{"day": 0, "price": "100"}, {"day": 1, "price": "90"}, {"day": 2, "price": "81"},
           {"day": 3, "price": "72.9"}, {"day": 4, "price": "65.6"}, {"day": 5, "price": "59"}]),
        m("illiquid", "流動性不足：處分連續六日無法全數成交", "Illiquid market: disposal unfilled for six days",
          [{"day": 0, "price": "100"}, {"day": 2, "price": "70"}, {"day": 5, "price": "55"}],
          unfilled_disposal_days=6, disposal_fill_ratio="0.3"),
        m("no_top_up", "收到補繳通知後未補繳", "Margin call not met",
          [{"day": 0, "price": "100"}, {"day": 2, "price": "75"}, {"day": 5, "price": "74"}]),
        m("residual_debt", "處分後仍有剩餘債務", "Remaining debt after disposal",
          [{"day": 0, "price": "100"}, {"day": 1, "price": "80"}, {"day": 2, "price": "70"}, {"day": 5, "price": "50"}]),
        d("dt_unmatched_long", "當沖買進後未完成賣出", "Day trade: bought but not sold", sell_quantity="1000",
          sell_price="102"),
        d("dt_unmatched_short", "先賣後買但未完成買回", "Day trade: sold first, not bought back",
          direction="sell_first", buy_quantity="1000", sell_quantity="2000",
          assumed_buyback_price="104", assumed_borrow_fee_rate="0.02"),
        d("dt_funding_gap", "交割資金不足", "Insufficient settlement funds", sell_quantity="0",
          direction="buy_first", available_cash="20000"),
        m("rule_change", "交易規則版本變更（虛構示範規則 140%）", "Rule version change (fictional 140% demo rule)",
          [{"day": 0, "price": "100"}, {"day": 1, "price": "82"}],
          rule_overrides={"MARGIN-CALL-THRESHOLD": "9.0.0-demo"}),
        m("contract_diff", "證券商契約條款不同（通知於次一營業日送達）", "Different broker terms (notice next day)",
          [{"day": 0, "price": "100"}, {"day": 2, "price": "70"}, {"day": 6, "price": "60"}],
          notice_served="next_trading_day"),
    ]
