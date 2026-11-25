"""計算 API 的輸入格式。金額與比率一律用字串傳（避免 JSON 浮點誤差），在後端轉 Decimal。"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

DecStr = str


def _dec(v: object) -> Decimal | None:
    if v is None or v == "":
        return None
    if isinstance(v, float):
        v = repr(v)
    try:
        d = Decimal(str(v).replace(",", "").strip())
    except Exception as e:  # noqa: BLE001
        raise ValueError("必須是數字") from e
    if not d.is_finite():
        raise ValueError("必須是有限數字")
    return d


class FeeIn(BaseModel):
    fee_rate: DecStr = "0.001425"
    fee_discount: DecStr = "1"
    min_fee: DecStr = "20"

    def dec(self) -> dict[str, Decimal]:
        return {k: _dec(getattr(self, k)) for k in ("fee_rate", "fee_discount", "min_fee")}


class MarginCalcIn(BaseModel):
    asset_label: str = Field("模擬資產", max_length=60)
    buy_price: DecStr
    quantity: DecStr
    financing_ratio: DecStr = "0.6"
    current_price: DecStr
    annual_interest_rate: DecStr | None = None
    holding_days: int = Field(0, ge=0, le=3650)
    day_basis: Literal[360, 365] = 365
    other_collateral_value: DecStr = "0"
    fees: FeeIn = FeeIn()
    as_of: date | None = None
    curve: bool = True

    @field_validator("buy_price", "quantity", "financing_ratio", "current_price", "other_collateral_value")
    @classmethod
    def _num(cls, v: str) -> str:
        _dec(v)
        return v


class DayTradeCalcIn(BaseModel):
    asset_label: str = Field("模擬資產", max_length=60)
    direction: Literal["buy_first", "sell_first"] = "buy_first"
    buy_price: DecStr
    buy_quantity: DecStr
    sell_price: DecStr
    sell_quantity: DecStr
    trade_date: date
    available_cash: DecStr = "0"
    fees: FeeIn = FeeIn()
    assumed_buyback_price: DecStr | None = None
    assumed_borrow_fee_rate: DecStr | None = None


class StepIn(BaseModel):
    day: int = Field(..., ge=0, le=250)
    price: DecStr
    label: str = Field("", max_length=60)
    action: Literal["none", "top_up", "add_collateral", "repay"] = "none"
    amount: DecStr = "0"


class MarginScenarioIn(BaseModel):
    asset_label: str = Field("模擬資產", max_length=60)
    buy_price: DecStr
    quantity: DecStr
    financing_ratio: DecStr = "0.6"
    start_date: date
    steps: list[StepIn] = Field(..., min_length=1, max_length=60)
    annual_interest_rate: DecStr | None = None
    fees: FeeIn = FeeIn()
    notice_served: Literal["same_day", "next_trading_day", "unknown"] = "same_day"
    unfilled_disposal_days: int = Field(0, ge=0, le=30)
    disposal_fill_ratio: DecStr = "1"
    other_collateral_value: DecStr = "0"
    rule_overrides: dict[str, str] | None = None


class PositionIn(BaseModel):
    label: str = Field(..., max_length=60)
    quantity: DecStr
    simulated_price: DecStr
    financing_principal: DecStr


class PortfolioCalcIn(BaseModel):
    positions: list[PositionIn] = Field(..., min_length=1, max_length=50)
    collateral_value: DecStr = "0"


def dec(v: object) -> Decimal | None:
    return _dec(v)
