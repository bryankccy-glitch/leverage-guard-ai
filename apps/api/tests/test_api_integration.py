"""API 整合測試：需要本機資料庫（./scripts/db_reset_local.sh 與 seed）。資料庫不可用時整組 skip。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.db import engine
from app.main import app


def _db_ok() -> bool:
    try:
        with engine().connect() as c:
            return c.execute(text("select count(*) from legal_articles")).scalar() > 0
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(not _db_ok(), reason="本機資料庫未啟動或未匯入")
client = TestClient(app)


def login(email: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/dev/login", json={"email": email})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


INV = "investor@demo.leverageguard.local"
INV2 = "investor2@demo.leverageguard.local"
REV = "reviewer@demo.leverageguard.local"
ADM = "admin@demo.leverageguard.local"

MARGIN = {"asset_label": "測試", "buy_price": "100", "quantity": "1000", "financing_ratio": "0.6",
          "start_date": "2026-12-01", "steps": [{"day": 0, "price": "100"}, {"day": 2, "price": "70"}]}


def test_guest_calculation_and_validation():
    r = client.post("/api/v1/calculate/margin", json={"buy_price": "100", "quantity": "1000", "financing_ratio": "0.6",
                                                      "current_price": "70", "curve": False})
    assert r.status_code == 200
    assert r.json()["metrics"]["margin_call_amount"]["value"] == "18000"
    assert r.headers["x-request-id"]
    bad = client.post("/api/v1/calculate/margin", json={"buy_price": "abc", "quantity": "1", "current_price": "1"})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "validation_error"


def test_unknown_account_cannot_login():
    assert client.post("/api/v1/auth/dev/login", json={"email": "hacker@example.com"}).status_code == 401
    assert client.get("/api/v1/simulations").status_code == 401
    assert client.get("/api/v1/simulations", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401


def test_rls_isolates_simulations_between_users():
    h1, h2 = login(INV2), login(INV)  # 測試資料建在第二個示範帳號，避免污染主要示範帳號
    r = client.post("/api/v1/simulations", headers=h1, json={"scenario_name": "隔離測試", "scenario_type": "margin",
                                                              "input_parameters": MARGIN})
    assert r.status_code == 201
    sid = r.json()["id"]
    assert client.get(f"/api/v1/simulations/{sid}", headers=h1).status_code == 200
    assert client.get(f"/api/v1/simulations/{sid}", headers=h2).status_code == 404
    assert client.get(f"/api/v1/simulations/{sid}", headers=login(ADM)).status_code == 404
    assert sid not in [i["id"] for i in client.get("/api/v1/simulations", headers=h2).json()["items"]]
    assert client.delete(f"/api/v1/simulations/{sid}", headers=h2).status_code == 404
    assert client.delete(f"/api/v1/simulations/{sid}", headers=h1).status_code == 204


def test_history_is_append_only():
    h1 = login(INV2)
    sid = client.post("/api/v1/simulations", headers=h1, json={"scenario_name": "歷史", "scenario_type": "margin",
                                                                "input_parameters": MARGIN}).json()["id"]
    client.post(f"/api/v1/simulations/{sid}/calculate", headers=h1)
    assert len(client.get(f"/api/v1/simulations/{sid}", headers=h1).json()["results"]) == 2
    with pytest.raises(DBAPIError, match="append-only"), engine().begin() as c:
        c.execute(text("update simulation_results set calculation_version = 'x'"))
    with pytest.raises(DBAPIError, match="append-only"), engine().begin() as c:
        c.execute(text("delete from audit_logs"))
    client.delete(f"/api/v1/simulations/{sid}", headers=h1)


def test_rule_review_permissions():
    assert client.post("/api/v1/admin/rules/TAX-GENERAL/review", headers=login(INV),
                       json={"version": "1.0.0", "decision": "approve"}).status_code == 403
    r = client.post("/api/v1/admin/rules/MARGIN-CALL-THRESHOLD/review", headers=login(REV),
                    json={"version": "9.0.0-demo", "decision": "activate"})
    assert r.status_code == 409  # 虛構示範規則不能啟用
    ok = client.post("/api/v1/admin/rules/TAX-GENERAL/review", headers=login(REV),
                     json={"version": "1.0.0", "decision": "approve", "notes": "核對證交稅條例第 2 條"})
    assert ok.status_code == 200 and ok.json()["review_status"] == "approved"
    client.post("/api/v1/admin/rules/TAX-GENERAL/review", headers=login(REV),
                json={"version": "1.0.0", "decision": "request_changes"})


def test_contract_upload_validation_and_isolation():
    h1, h2 = login(INV2), login(INV)
    no_ack = client.post("/api/v1/contracts/upload", headers=h1, files={"file": ("a.txt", "第1條 測試".encode(), "text/plain")})
    assert no_ack.status_code == 422
    fake = client.post("/api/v1/contracts/upload", headers=h1, data={"acknowledge_privacy": "true"},
                       files={"file": ("x.pdf", b"MZ\x90\x00 not a pdf", "application/pdf")})
    assert fake.status_code == 415
    up = client.post("/api/v1/contracts/upload", headers=h1, data={"acknowledge_privacy": "true"},
                     files={"file": ("c.txt", "第一條 維持率低於 130% 時應補繳。".encode(), "text/plain")})
    assert up.status_code == 201
    cid = up.json()["id"]
    assert client.get(f"/api/v1/contracts/{cid}", headers=h1).status_code == 200
    assert client.get(f"/api/v1/contracts/{cid}", headers=h2).status_code == 404
    assert client.get(f"/api/v1/contracts/{cid}", headers=login(ADM)).status_code == 404
    assert client.get(f"/api/v1/contracts/{cid}/file?sig=1.bad", headers=h1).status_code == 403
    assert client.delete(f"/api/v1/contracts/{cid}", headers=h1).status_code == 204


def test_copilot_refuses_investment_advice():
    r = client.post("/api/v1/copilot/guest", json={"message": "我現在應不應該賣出？哪一支股票適合融資？"})
    assert r.status_code == 200 and r.json()["kind"] == "refusal"
    r2 = client.post("/api/v1/copilot/guest", json={"message": "怎麼樣才能逃避交割責任"})
    assert r2.json()["kind"] == "refusal"


def test_public_legal_and_rules():
    docs = client.get("/api/v1/legal/documents").json()["items"]
    assert {d["source_key"] for d in docs} >= {"twse:FL007121", "twse:FL071871", "moj:G0340078"}
    s = client.get("/api/v1/legal/search", params={"q": "第54條", "mode": "keyword"}).json()
    assert any(i["article"]["article_number"] == "第54條" for i in s["items"])
    rules = client.get("/api/v1/rules").json()["items"]
    assert any(r["rule_id"] == "MARGIN-CALL-THRESHOLD" and len(r["versions"]) == 2 for r in rules)
    assert client.get("/api/v1/admin/users", headers=login(INV)).status_code == 403


def test_report_from_completed_run(monkeypatch):
    """不依賴 LLM：關閉生成式 AI，用規則模板完成分析，再產生報告與三種匯出。"""
    from app.agents import llm, workflow
    monkeypatch.setattr(llm, "provider_info", lambda: {"provider": "none", "model": None, "configured": False})
    h = login(INV2)
    sid = client.post("/api/v1/simulations", headers=h, json={"scenario_name": "報告測試", "scenario_type": "margin",
                                                               "input_parameters": MARGIN}).json()["id"]
    run_id, _ = workflow.create_run(None, "simulation_analysis", {"t": "margin", "p": MARGIN, "sid": sid}, scenario_id=sid)
    from app.core.db import service_session
    with service_session() as c:
        c.execute(text("update agent_runs set user_id = (select id from profiles where email = :e) where id = :i"),
                  {"e": INV2, "i": run_id})
    workflow.run_simulation_analysis(run_id, "margin", MARGIN)
    r = client.post("/api/v1/reports", headers=h, json={"run_id": run_id, "report_type": "investor"})
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    for fmt, ctype in (("pdf", "application/pdf"), ("json", "application/json"), ("csv", "text/csv")):
        e = client.get(f"/api/v1/reports/{rid}/export?format={fmt}", headers=h)
        assert e.status_code == 200 and e.headers["content-type"].startswith(ctype)
    assert client.get(f"/api/v1/reports/{rid}", headers=login(INV)).status_code == 404
    notes = client.get("/api/v1/notifications", headers=h).json()["items"]
    assert any(n["notification_type"] == "report_generated" for n in notes)
    client.delete(f"/api/v1/simulations/{sid}", headers=h)
