"""從資料庫讀取人工審查後的規則狀態（例如審查員核准為 active），提供給規則引擎。"""
from __future__ import annotations

import time

from ..core.db import rows, service_session

_cache: tuple[float, dict[str, str]] | None = None


def status_overrides(ttl: float = 15.0) -> dict[str, str]:
    global _cache
    now = time.monotonic()
    if _cache and now - _cache[0] < ttl:
        return _cache[1]
    try:
        with service_session() as conn:
            data = {f"{r['rule_key']}@{r['version']}": r["review_status"] for r in rows(conn, """
                select r.rule_key, v.version, v.review_status from legal_rule_versions v
                join legal_rules r on r.id = v.rule_id""")}
    except Exception:  # noqa: BLE001 - 資料庫暫時無法連線時退回檔案內的狀態
        data = {}
    _cache = (now, data)
    return data


def invalidate() -> None:
    global _cache
    _cache = None
