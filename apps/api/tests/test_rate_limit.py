"""限流：真實 IP、token 不落地、單機與跨實例（資料庫）計數。"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from starlette.requests import Request

from app.core import middleware
from app.core.config import get_settings
from app.core.db import engine
from app.main import app

client = TestClient(app)


def _req(headers: dict[str, str], host: str = "10.0.0.1") -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw, "client": (host, 1234)})


def test_client_ip_uses_forwarded_header_only_when_serverless(monkeypatch):
    r = _req({"x-forwarded-for": "203.0.113.7, 10.1.1.1"})
    monkeypatch.setattr(get_settings(), "serverless", False)
    assert middleware.client_ip(r) == "10.0.0.1"  # 本機不信任可偽造的標頭
    monkeypatch.setattr(get_settings(), "serverless", True)
    assert middleware.client_ip(r) == "203.0.113.7"


def test_rate_key_hashes_authorization():
    token = "Bearer secret-token-value-1234567890"
    key = middleware.rate_key(_req({"authorization": token}))
    assert "secret" not in key and "1234567890" not in key
    assert key != middleware.rate_key(_req({"authorization": token + "x"}))  # 不同帳號分開計數
    assert middleware.rate_key(_req({})).endswith(":-")


def test_memory_limit_returns_429(monkeypatch):
    monkeypatch.setattr(get_settings(), "serverless", False)
    monkeypatch.setattr(get_settings(), "rate_limit_per_minute", 3)
    middleware._hits.clear()
    headers = {"authorization": f"Bearer {uuid.uuid4().hex}"}
    codes = [client.get("/api/v1/legal/documents", headers=headers).status_code for _ in range(4)]
    assert codes[:3] != [429, 429, 429] and codes[3] == 429
    assert client.get("/api/v1/health", headers=headers).status_code == 200  # 健康檢查不受限流
    middleware._hits.clear()


def _db_ready() -> bool:
    try:
        with engine().connect() as c:
            return c.execute(text("select to_regclass('public.api_rate_limits') is not null")).scalar()
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.skipif(not _db_ready(), reason="本機資料庫未啟動或未套用 api_rate_limits migration")
def test_db_counter_is_shared_and_atomic():
    key = f"test:{uuid.uuid4().hex}"
    try:
        counts = [middleware._db_hits(key) for _ in range(5)]
        assert counts == [1, 2, 3, 4, 5]
        middleware._hits.clear()  # 模擬另一個實例（記憶體是空的），資料庫仍記得
        assert middleware._db_hits(key) == 6
    finally:
        with engine().begin() as c:
            c.execute(text("delete from public.api_rate_limits where bucket = :b"), {"b": key})


@pytest.mark.skipif(not _db_ready(), reason="本機資料庫未啟動或未套用 api_rate_limits migration")
def test_serverless_falls_back_to_memory_when_db_fails(monkeypatch):
    import asyncio

    monkeypatch.setattr(get_settings(), "serverless", True)

    def boom(_key: str) -> int:
        raise RuntimeError("db down")

    monkeypatch.setattr(middleware, "_db_hits", boom)
    middleware._hits.clear()
    assert asyncio.run(middleware.count_hit("fallback-key")) == 1
    middleware._hits.clear()
