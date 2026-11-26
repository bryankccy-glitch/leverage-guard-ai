"""真實帳號模式（AUTH_MODE=supabase）：新帳號只看到自己的紀錄，不出現全站示範內容。需要本機資料庫。"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import engine
from app.main import app
from app.security import auth


def _db_ok() -> bool:
    try:
        with engine().connect() as c:
            return c.execute(text("select count(*) from regulatory_updates where is_demo")).scalar() > 0
    except Exception:  # noqa: BLE001
        return False

pytestmark = pytest.mark.skipif(not _db_ok(), reason="本機資料庫未啟動或未匯入")
client = TestClient(app)


@pytest.fixture
def new_account(monkeypatch):
    """模擬一個剛建立、從未使用過的 Supabase 帳號（例如 bryan）。"""
    uid = str(uuid.uuid4())
    email = f"t{uid[:8]}@leverageguard.local"
    with engine().begin() as c:
        c.execute(text("insert into auth.users (id, email, aud, role) values (:i, :e, 'authenticated', 'authenticated')"),
                  {"i": uid, "e": email})
    get_settings.cache_clear()
    monkeypatch.setenv("AUTH_MODE", "supabase")
    monkeypatch.setattr(auth, "_decode_supabase", lambda token: {"sub": uid, "email": email, "role": "authenticated"})
    yield {"Authorization": "Bearer test-token"}
    get_settings.cache_clear()
    with engine().begin() as c:
        c.execute(text("delete from profiles where id = :i"), {"i": uid})
        c.execute(text("delete from auth.users where id = :i"), {"i": uid})


def test_demo_mode_still_shows_demo_update():
    get_settings.cache_clear()
    items = client.get("/api/v1/regulatory/updates").json()["items"]
    assert any(i["is_demo"] for i in items)


def test_new_account_sees_only_own_records(new_account):
    d = client.get("/api/v1/dashboard", headers=new_account)
    assert d.status_code == 200, d.text
    d = d.json()
    assert d["kpis"]["scenarios"] == 0 and d["kpis"]["contracts"] == 0 and d["kpis"]["reports"] == 0
    assert d["recent_simulations"] == [] and d["risk_overview"] == [] and d["account"] is None
    assert not any(u["is_demo"] for u in d["regulatory_updates"])
    assert client.get("/api/v1/history", headers=new_account).json()["items"] == []


def test_account_mode_hides_demo_regulatory_update(new_account):
    items = client.get("/api/v1/regulatory/updates").json()["items"]
    assert not any(i["is_demo"] for i in items)
    with engine().connect() as c:
        demo_id = c.execute(text("select id::text from regulatory_updates where is_demo limit 1")).scalar()
    assert client.get(f"/api/v1/regulatory/updates/{demo_id}").status_code == 404


def test_account_mode_has_no_demo_contract(new_account):
    assert client.post("/api/v1/contracts/demo", headers=new_account).status_code == 404
