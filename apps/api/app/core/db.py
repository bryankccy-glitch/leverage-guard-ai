"""資料庫連線。

使用者請求一律在交易內切換成 `authenticated` 角色並帶入 JWT claims，讓 PostgreSQL 的 RLS 真的生效；
系統工作（匯入法規、Agent 背景任務）用 service_session（切換成 service_role），程式碼裡明確可見。
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from .config import get_settings


@lru_cache
def engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True, pool_size=5, max_overflow=10)


@contextmanager
def user_session(claims: dict[str, Any] | None) -> Iterator[Connection]:
    """claims 為 None 代表訪客（anon）。"""
    with engine().begin() as conn:
        if claims is None:
            conn.execute(text("select set_config('request.jwt.claims', '', true)"))
            conn.execute(text("set local role anon"))
        else:
            conn.execute(text("select set_config('request.jwt.claims', :c, true)"), {"c": json.dumps(claims)})
            conn.execute(text("set local role authenticated"))
        yield conn


@contextmanager
def service_session() -> Iterator[Connection]:
    with engine().begin() as conn:
        conn.execute(text("set local role service_role"))
        yield conn


def rows(conn: Connection, sql: str, **params: Any) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params)]


def one(conn: Connection, sql: str, **params: Any) -> dict[str, Any] | None:
    r = conn.execute(text(sql), params).first()
    return None if r is None else dict(r._mapping)
