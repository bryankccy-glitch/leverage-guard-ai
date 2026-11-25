"""整戶擔保維持率（只含融資部位與抵繳品；不含融券）。

整戶維持率＝（各融資部位市值合計＋抵繳品市值）÷ 各融資部位融資金額合計 × 100%
（依操作辦法第 53 條公式，融券項為 0）。不可把各部位維持率直接平均。
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .rounding import HUNDRED, ZERO, money, ratio_pct, safe_div
from .types import Metric
from .validation import Validator


@dataclass
class PositionLine:
    label: str
    quantity: Decimal
    simulated_price: Decimal
    financing_principal: Decimal


def account_ratio(positions: list[PositionLine], collateral_value: Decimal = ZERO) -> dict[str, Metric]:
    v = Validator()
    if not positions:
        v.add("positions", "required", "至少需要一個融資部位")
    for n, p in enumerate(positions):
        v.positive(f"positions[{n}].quantity", p.quantity, "股數")
        v.positive(f"positions[{n}].simulated_price", p.simulated_price, "模擬價格")
        v.non_negative(f"positions[{n}].financing_principal", p.financing_principal, "融資金額")
    v.non_negative("collateral_value", collateral_value, "抵繳品市值")
    v.raise_if_any()
    mv = sum((money(p.quantity * p.simulated_price) for p in positions), ZERO)
    debt = sum((p.financing_principal for p in positions), ZERO)
    ratio = safe_div(mv + collateral_value, debt)
    return {
        "account_market_value": Metric("account_market_value", "整戶融資部位市值", mv, "TWD", "Σ 股數 × 模擬價格", {}),
        "account_debt": Metric("account_debt", "整戶融資金額", debt, "TWD", "Σ 融資金額", {}),
        "account_maintenance_ratio": Metric(
            "account_maintenance_ratio", "整戶擔保維持率", None if ratio is None else ratio_pct(ratio * HUNDRED),
            "percent", "(Σ市值 ＋ 抵繳品市值) ÷ Σ融資金額 × 100%", {"抵繳品市值": str(collateral_value)},
            ["MARGIN-RATIO-FORMULA"], simplified=True, note="不含融券部位"),
    }
