"""計算結果的共用型別：每個數字都帶公式、輸入、規則與是否為簡化估算。"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class Metric:
    key: str
    label: str
    value: Decimal | None
    unit: str  # "TWD" | "percent" | "price" | "shares" | "days"
    formula: str
    inputs: dict[str, str] = field(default_factory=dict)
    rule_ids: list[str] = field(default_factory=list)
    simplified: bool = False
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["value"] = None if self.value is None else str(self.value)
        return d


@dataclass
class CalcWarning:
    code: str
    message: str


def serialize(obj: Any) -> Any:
    """把 Decimal 轉字串，保留精度給前端與資料庫。"""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, Metric):
        return obj.to_dict()
    if isinstance(obj, CalcWarning):
        return {"code": obj.code, "message": obj.message}
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [serialize(v) for v in obj]
    if hasattr(obj, "__dataclass_fields__"):
        return {k: serialize(v) for k, v in asdict(obj).items()}
    return obj
