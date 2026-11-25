"""抵繳擔保品的折算價值。

折算比例（證券商辦理有價證券買賣融資融券業務操作辦法 第 59 條）：
中央登錄公債按面額九折；地方政府債券、公司債、金融債按面額七折；
得為融資融券的上市（櫃）有價證券按基準價七折；未取得或暫停融資融券資格者按五折。
其他類別（興櫃、黃金、基金）規則較複雜，這裡不估算，回傳 None 並提示。
"""
from __future__ import annotations

from decimal import Decimal

from .rounding import D, money

HAIRCUTS: dict[str, Decimal] = {
    "central_government_bond": D("0.9"),
    "local_government_or_corporate_bond": D("0.7"),
    "margin_eligible_listed_security": D("0.7"),
    "non_margin_eligible_listed_security": D("0.5"),
}


def collateral_value(asset_type: str, base_value: Decimal) -> Decimal | None:
    rate = HAIRCUTS.get(asset_type)
    return None if rate is None else money(base_value * rate)
