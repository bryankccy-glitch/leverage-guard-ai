"""輸入驗證：錯誤一律帶欄位名稱與錯誤代碼，前端可以直接標在欄位旁。"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .rounding import ONE, ZERO


@dataclass
class FieldError:
    field: str
    code: str
    message: str


@dataclass
class CalculationInputError(Exception):
    errors: list[FieldError] = field(default_factory=list)

    def __str__(self) -> str:
        return "; ".join(f"{e.field}: {e.message}" for e in self.errors)


class Validator:
    def __init__(self) -> None:
        self.errors: list[FieldError] = []

    def positive(self, name: str, value: Decimal | None, label: str) -> None:
        if value is None:
            self.errors.append(FieldError(name, "required", f"{label}為必填"))
        elif value <= ZERO:
            self.errors.append(FieldError(name, "must_be_positive", f"{label}必須大於 0"))

    def non_negative(self, name: str, value: Decimal | None, label: str) -> None:
        if value is not None and value < ZERO:
            self.errors.append(FieldError(name, "must_be_non_negative", f"{label}不能是負數"))

    def integer(self, name: str, value: Decimal | None, label: str) -> None:
        if value is not None and value != value.to_integral_value():
            self.errors.append(FieldError(name, "must_be_integer", f"{label}必須是整數"))

    def open_unit_interval(self, name: str, value: Decimal | None, label: str) -> None:
        if value is None:
            self.errors.append(FieldError(name, "required", f"{label}為必填"))
        elif not (ZERO < value < ONE):
            self.errors.append(FieldError(name, "out_of_range", f"{label}必須介於 0 與 1 之間（不含）"))

    def rate(self, name: str, value: Decimal | None, label: str, maximum: Decimal = ONE) -> None:
        if value is not None and not (ZERO <= value <= maximum):
            self.errors.append(FieldError(name, "out_of_range", f"{label}必須介於 0 與 {maximum} 之間"))

    def add(self, name: str, code: str, message: str) -> None:
        self.errors.append(FieldError(name, code, message))

    def raise_if_any(self) -> None:
        if self.errors:
            raise CalculationInputError(self.errors)
