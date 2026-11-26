"""英文介面：Accept-Language: en 時回應不得出現中文（官方條文原文等刻意保留的欄位除外），且數字與中文版相同。"""
from __future__ import annotations

import re
from typing import Any

import pytest
from fastapi.testclient import TestClient
from test_api_integration import INV, MARGIN, _db_ok, login

from app import i18n
from app.agents.guards import advice_violations, is_advice_request, misconceptions
from app.main import app

CJK = re.compile(r"[一-鿿]")
EN = {"Accept-Language": "en"}
client = TestClient(app)
# 刻意保留原文的欄位：官方條文、契約原文、只在中文介面用的標題、使用者自己輸入的名稱
KEEP = i18n.SKIP_KEYS | {"title_zh", "chapter"}


def leftovers(obj: Any, key: str | None = None) -> list[str]:
    if key in KEEP:
        return []
    if isinstance(obj, str):
        return [obj] if CJK.search(obj) else []
    if isinstance(obj, list):
        return [s for v in obj for s in leftovers(v, key)]
    if isinstance(obj, dict):
        out = [k for k in obj if isinstance(k, str) and CJK.search(k)]
        return out + [s for k, v in obj.items() for s in leftovers(v, k)]
    return []


def numbers(obj: Any) -> list[str]:
    if isinstance(obj, dict):
        return [n for k in sorted(obj) for n in numbers(obj[k])]
    if isinstance(obj, list):
        return [n for v in obj for n in numbers(v)]
    if isinstance(obj, str):
        return [obj] if re.fullmatch(r"-?\d+(?:\.\d+)?", obj) else []
    if isinstance(obj, int | float) and not isinstance(obj, bool):
        return [str(obj)]
    return []


# ───────── 不需要資料庫
def test_accept_language_parsing():
    assert i18n.parse_accept_language("en-US,en;q=0.9") == "en"
    assert i18n.parse_accept_language("zh-TW,zh;q=0.9,en;q=0.8") == "zh-TW"
    assert i18n.parse_accept_language(None) == "zh-TW"
    assert i18n.parse_accept_language("fr") == "zh-TW"


def test_translate_keeps_official_text_and_translates_templates():
    out = i18n.translate({"quote": "證券商應逐日計算", "content": "第一條", "rule_name": "補繳期限",
                          "msg": "維持率 120.5% 低於門檻 130.0%", "err": "買入價格為必填", "art": "第54條"})
    assert out["quote"] == "證券商應逐日計算" and out["content"] == "第一條"
    assert out["rule_name"] == "Top-up deadline"
    assert out["msg"] == "Ratio 120.5% below the 130.0% threshold"
    assert out["err"] == "Buy price is required"
    assert out["art"] == "Art. 54"


def test_every_rule_has_english_name_and_explanation():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[3]
    rules = json.loads((root / "data/rules/rules.json").read_text())["rules"]
    for r in rules:
        for f in ("rule_name", "plain_language", "investor_rights", "investor_obligations", "broker_rights",
                  "broker_obligations", "required_evidence", "exceptions"):
            v = r.get(f)
            for s in v if isinstance(v, list) else [v] if v else []:
                assert not CJK.search(i18n.tr(s)), f"{r['rule_id']}.{f} 沒有英文：{s}"


def test_english_review_gate_blocks_advice_and_misconceptions():
    assert advice_violations("You should sell now; it is risk-free with a guaranteed profit.")
    assert advice_violations("Target price is 120.")
    assert not advice_violations("The broker may dispose of collateral if you do not top up by the deadline.")
    assert misconceptions("Top up to restore the maintenance ratio back to 130%.")
    assert is_advice_request("Should I buy more on margin?")
    assert is_advice_request("Which stock should I pick?")
    assert not is_advice_request("How is the maintenance ratio calculated?")


# ───────── 需要本機資料庫
db = pytest.mark.skipif(not _db_ok(), reason="本機資料庫未啟動或未匯入")
MARGIN_CALC = {"asset_label": "Demo", "buy_price": "100", "quantity": "1000", "financing_ratio": "0.6",
               "current_price": "75", "annual_interest_rate": "0.0645", "holding_days": 30, "curve": True}
DAY = {"asset_label": "Demo", "direction": "sell_first", "buy_price": "100", "buy_quantity": "1000",
       "sell_price": "102", "sell_quantity": "2000", "trade_date": "2027-03-02", "available_cash": "20000",
       "assumed_buyback_price": "104", "assumed_borrow_fee_rate": "0.02"}


@db
@pytest.mark.parametrize(("method", "path", "body"), [
    ("post", "/api/v1/calculate/margin", MARGIN_CALC),
    ("post", "/api/v1/calculate/day-trading", DAY),
    ("post", "/api/v1/calculate/day-trading", {**DAY, "direction": "buy_first",
                                               "buy_quantity": "3000", "available_cash": "0"}),
    ("post", "/api/v1/calculate/scenario", {**MARGIN, "asset_label": "Demo",
                                             "steps": [{"day": 0, "price": "100"}, {"day": 1, "price": "70"},
                                                       {"day": 4, "price": "45"}]}),
    ("post", "/api/v1/calculate/portfolio", {"positions": [{"label": "A", "quantity": "1000", "simulated_price": "60",
                                                            "financing_principal": "60000"}], "collateral_value": "0"}),
    ("get", "/api/v1/calculate/presets", None),
    ("get", "/api/v1/rules", None),
    ("get", "/api/v1/legal/rights", None),
    ("get", "/api/v1/legal/obligations", None),
    ("get", "/api/v1/legal/documents", None),
])
def test_public_endpoints_have_no_chinese_in_english(method: str, path: str, body: dict | None):
    r = getattr(client, method)(path, headers=EN, **({"json": body} if body else {}))
    assert r.status_code in (200, 201), r.text
    assert leftovers(r.json()) == []


@db
def test_english_validation_errors():
    r = client.post("/api/v1/calculate/margin", headers=EN, json={"buy_price": "abc", "quantity": "1", "current_price": "1"})
    assert r.status_code == 422
    assert leftovers(r.json()) == []


@db
def test_english_numbers_match_chinese():
    zh = client.post("/api/v1/calculate/margin", json=MARGIN_CALC).json()
    en = client.post("/api/v1/calculate/margin", headers=EN, json=MARGIN_CALC).json()
    # 鍵會被翻譯、順序可能不同，所以比較排序後的數字集合
    assert sorted(numbers(zh["metrics"])) == sorted(numbers(en["metrics"]))
    assert zh["metrics"]["maintenance_ratio"]["value"] == en["metrics"]["maintenance_ratio"]["value"]
    # 不帶 Accept-Language 時維持中文
    assert CJK.search(zh["metrics"]["financing"]["label"])


@db
def test_signed_in_pages_have_no_chinese_in_english():
    h = {**login(INV), **EN}
    for path in ("/api/v1/dashboard", "/api/v1/simulations", "/api/v1/accounts", "/api/v1/notifications",
                 "/api/v1/history", "/api/v1/me"):
        r = client.get(path, headers=h)
        assert r.status_code == 200, (path, r.text)
        assert leftovers(r.json()) == [], path
    sims = client.get("/api/v1/simulations", headers=h).json()["items"]
    if sims:
        sid = sims[0]["id"]
        for path in (f"/api/v1/simulations/{sid}", f"/api/v1/simulations/{sid}/timeline"):
            r = client.get(path, headers=h)
            if r.status_code == 404 and path.endswith("/timeline"):
                assert leftovers(r.json()) == [], path  # 尚未計算：錯誤訊息也要是英文
                continue
            assert r.status_code == 200, (path, r.text)
            assert leftovers(r.json()) == [], path


@db
def test_new_scenario_timeline_and_lists_in_english():
    h = {**login(INV), **EN}
    sid = client.post("/api/v1/simulations", headers=h, json={
        "scenario_name": "i18n test", "scenario_type": "margin",
        "input_parameters": {**MARGIN, "asset_label": "Demo",
                             "steps": [{"day": 0, "price": "100"}, {"day": 1, "price": "70"}, {"day": 4, "price": "45"}]},
    }).json()["id"]
    for path in (f"/api/v1/simulations/{sid}", f"/api/v1/simulations/{sid}/timeline", "/api/v1/contracts",
                 "/api/v1/agents/runs", "/api/v1/reports", "/api/v1/agents"):
        r = client.get(path, headers=h)
        assert r.status_code == 200, (path, r.text)
        assert leftovers(r.json()) == [], path
    client.delete(f"/api/v1/simulations/{sid}", headers=h)


@db
def test_reviewer_pages_in_english():
    from test_api_integration import REV
    h = {**login(REV), **EN}
    updates = client.get("/api/v1/regulatory/updates", headers=h)
    assert updates.status_code == 200 and leftovers(updates.json()) == []
    for path in ("/api/v1/admin/review-queue", "/api/v1/admin/evaluation"):
        r = client.get(path, headers=h)
        assert r.status_code == 200, (path, r.text)
        assert leftovers(r.json()) == [], path
    items = updates.json().get("items") or []
    if items:
        uid = items[0]["id"]
        for path in (f"/api/v1/regulatory/updates/{uid}", f"/api/v1/regulatory/updates/{uid}/impact"):
            r = client.get(path, headers=h)
            assert r.status_code == 200, (path, r.text)
            assert leftovers(r.json()) == [], path


@db
def test_guest_copilot_refusal_includes_objective_risk_facts():
    ctx = {"trading_type": "margin", "input": {"asset_label": "Demo", "buy_price": "100", "quantity": "1000",
                                               "financing_ratio": "0.6", "current_price": "100"}}
    zh = client.post("/api/v1/copilot/guest", json={"message": "我現在該不該融資買進？", "context": ctx})
    assert zh.status_code == 200 and zh.json()["kind"] == "refusal"
    facts = zh.json()["risk_facts"]
    assert any("2.50%" in f for f in facts) and any("78.00" in f for f in facts)
    en = client.post("/api/v1/copilot/guest", headers=EN, json={"message": "Should I buy on margin right now?", "context": ctx})
    assert en.status_code == 200 and en.json()["kind"] == "refusal"
    assert leftovers(en.json()) == []
