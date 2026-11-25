"""金額與比率的進位規則。所有金額都用 Decimal，不使用浮點數。"""
from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

CALCULATION_VERSION = "fin-engine-1.0.0"

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")

ROUNDING_MODES = {"half_up": ROUND_HALF_UP, "down": ROUND_DOWN}


def D(value: object) -> Decimal:
    """轉成 Decimal；拒絕 float（避免 0.1 這類二進位誤差混進金額）。"""
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, bool):
        raise TypeError("布林值不能當數字")
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, str):
        try:
            result = Decimal(value.strip().replace(",", ""))
        except InvalidOperation as exc:
            raise ValueError(f"不是合法數字：{value!r}") from exc
    elif isinstance(value, float):
        raise TypeError("金額不接受 float，請傳字串或 Decimal")
    else:
        raise TypeError(f"不支援的數字型別：{type(value).__name__}")
    if not result.is_finite():
        raise ValueError("數字必須是有限值")
    return result


def money(value: Decimal, mode: str = "half_up") -> Decimal:
    """新臺幣金額：取到元。"""
    return value.quantize(ONE, rounding=ROUNDING_MODES[mode])


def ratio_pct(value: Decimal) -> Decimal:
    """百分比取到小數點後兩位（例如 133.33）。"""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def price(value: Decimal) -> Decimal:
    """股價取到小數點後兩位。"""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def safe_div(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    """分母為 0 時回傳 None，由呼叫端決定如何呈現（不產生無限大或 NaN）。"""
    if denominator == ZERO:
        return None
    with localcontext() as ctx:
        ctx.prec = 28
        return numerator / denominator
