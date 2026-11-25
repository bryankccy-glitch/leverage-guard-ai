"""交易日曆：週末＋臺灣證券交易所公告的休市日。

資料：data/legal/twse_holidays.json（由 scripts/extract_legal_sources.py 從證交所下載）。
證交所只公布最新年度，資料未涵蓋的年份只排除週末，並在結果標示 coverage = "weekends_only"。
「市場無交易，僅辦理結算交割作業」的日子算非交易日。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[4] / "data" / "legal" / "twse_holidays.json"


@dataclass(frozen=True)
class CalendarResult:
    date: date
    coverage: str  # "official" | "weekends_only"
    note: str | None = None


@lru_cache(maxsize=1)
def _holidays() -> tuple[frozenset[date], frozenset[int], str | None]:
    if not DATA.exists():
        return frozenset(), frozenset(), None
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    days = frozenset(date.fromisoformat(d) for d in raw["non_trading_days"])
    years = frozenset(d.year for d in days)
    return days, years, raw.get("source_url")


def is_trading_day(d: date) -> bool:
    days, _, _ = _holidays()
    return d.weekday() < 5 and d not in days


def coverage_for(d: date) -> str:
    _, years, _ = _holidays()
    return "official" if d.year in years else "weekends_only"


def add_trading_days(start: date, n: int) -> CalendarResult:
    """從 start 往後數 n 個交易日（start 當天不算）。"""
    if n < 0:
        raise ValueError("n 必須 ≥ 0")
    d, count = start, 0
    covered = {coverage_for(start)}
    while count < n:
        d += timedelta(days=1)
        covered.add(coverage_for(d))
        if is_trading_day(d):
            count += 1
    cov = "official" if covered == {"official"} else "weekends_only"
    note = None if cov == "official" else "此期間部分日期不在證交所已公告的休市日資料內，僅排除週末，實際期限可能不同"
    return CalendarResult(d, cov, note)


def next_trading_day(d: date) -> CalendarResult:
    return add_trading_days(d, 1)
