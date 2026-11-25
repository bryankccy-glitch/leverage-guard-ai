"""法規監察（公開讀取）與管理／審查 API（legal_reviewer、system_admin）。"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text

from ..core.audit import audit
from ..core.config import ROOT
from ..core.db import one, rows, service_session, user_session
from ..core.errors import ApiError
from ..financial_engine.rounding import D
from ..legal_rules.engine import all_rule_versions
from ..regulatory_monitor.monitor import check_for_updates
from ..scenario_engine.margin_scenario import MarginScenarioInput, Step, run_margin_scenario
from ..security.auth import Principal, require_role
from ..services.rule_status import invalidate, status_overrides

router = APIRouter()
Reviewer = Depends(require_role("legal_reviewer", "system_admin"))
Admin = Depends(require_role("system_admin"))


# ───── 法規變動（公開讀取） ─────
@router.get("/regulatory/updates", tags=["regulatory"])
def updates() -> dict:
    with user_session(None) as conn:
        items = rows(conn, """select id::text, title, authority, official_url, change_summary, affected_trading_types,
                                is_demo, review_status, publication_date::text, effective_date::text, detected_at::text
                              from regulatory_updates order by detected_at desc""")
    return {"items": items}


@router.get("/regulatory/updates/{uid}", tags=["regulatory"])
def update_detail(uid: str) -> dict:
    with user_session(None) as conn:
        u = one(conn, """select id::text, title, authority, official_url, change_summary, changed_articles, diff,
                           affected_trading_types, impact_analysis, is_demo, review_status, publication_date::text,
                           effective_date::text, detected_at::text, draft_rule_version_id::text
                         from regulatory_updates where id::text = :i""", i=uid)
    if u is None:
        raise ApiError(404, "not_found", "找不到法規更新")
    return json.loads(json.dumps(u, default=str))


@router.get("/regulatory/updates/{uid}/impact", tags=["regulatory"])
def update_impact(uid: str) -> dict:
    """以示範情境 A 比較新舊規則版本：同一情境重新計算，列出法律事件差異。"""
    u = update_detail(uid)
    if not u["draft_rule_version_id"]:
        return {"update": u, "comparison": None, "note": "此更新尚未對應到可比較的規則草案"}
    start = date.today()
    steps = [Step(0, D("100")), Step(1, D("82")), Step(3, D("75"))]
    base = dict(buy_price=D("100"), quantity=D("1000"), financing_ratio=D("0.6"), start_date=start, steps=steps)
    old = run_margin_scenario(MarginScenarioInput(**base, status_overrides=status_overrides()))
    new = run_margin_scenario(MarginScenarioInput(**base, rule_overrides={"MARGIN-CALL-THRESHOLD": "9.0.0-demo"},
                                                  include_demo_rules=True, status_overrides=status_overrides()))
    pick = lambda r: [{"date": n["date"], "event_type": n["event_type"], "title": n["title_zh"], "status": n["status"]}  # noqa: E731
                      for n in r["timeline"] if n["event_type"] not in ("price_change",)]
    return {"update": u, "comparison": {
        "scenario": "示範情境：100 元買進 1,000 股、融資六成，股價 82 → 75 元",
        "old": {"rule_version": old["rule_version"], "threshold": old["parameters"]["maintenance_threshold"],
                "events": pick(old)},
        "new": {"rule_version": new["rule_version"], "threshold": new["parameters"]["maintenance_threshold"],
                "events": pick(new)}},
        "note": "示範規則為虛構，僅展示版本差異與重新計算；不會套用到正式計算。"}


# ───── 規則審查 ─────
class RuleReviewIn(BaseModel):
    version: str = Field(..., max_length=40)
    decision: Literal["approve", "activate", "suspend", "reject", "request_changes"]
    notes: str = Field("", max_length=2000)


STATUS_FOR = {"approve": "approved", "activate": "active", "suspend": "suspended", "reject": "superseded",
              "request_changes": "pending_review"}


@router.post("/admin/rules/{rule_id}/review", tags=["admin"])
def review_rule(rule_id: str, body: RuleReviewIn, request: Request, user: Principal = Reviewer) -> dict:
    rv = next((r for r in all_rule_versions() if r.rule_id == rule_id and r.version == body.version), None)
    if rv is None:
        raise ApiError(404, "not_found", "找不到規則版本")
    if body.decision in ("approve", "activate") and rv.raw.get("sources") and not rv.citation_ok:
        raise ApiError(409, "conflict", "引用驗證未通過的規則不能核准")
    if body.decision == "activate" and rv.is_demo and rv.raw.get("sources"):
        raise ApiError(409, "conflict", "虛構示範規則不能啟用到正式計算")
    with user_session(user.claims) as conn:
        ver = one(conn, """select v.id::text, v.review_status from legal_rule_versions v join legal_rules r on r.id = v.rule_id
                           where r.rule_key = :k and v.version = :v""", k=rule_id, v=body.version)
        if ver is None:
            raise ApiError(404, "not_found", "規則版本尚未匯入資料庫")
        status = STATUS_FOR[body.decision]
        conn.execute(text("""update legal_rule_versions set review_status = :s, reviewed_by = auth.uid(),
                             approved_at = case when :s in ('approved','active') then now() else approved_at end
                             where id = cast(:i as uuid)"""), {"s": status, "i": ver["id"]})
        conn.execute(text("""insert into reviews (reviewer_id, resource_type, resource_id, decision, notes)
                             values (auth.uid(), 'rule_version', cast(:i as uuid), :d, :n)"""),
                     {"i": ver["id"], "d": body.decision, "n": body.notes})
    invalidate()
    audit(request, user.id, f"rule.{body.decision}", "rule_version", ver["id"], {"rule": rule_id, "version": body.version})
    if status == "active":
        _notify_rule_change(rule_id, body.version)
    return {"rule_id": rule_id, "version": body.version, "review_status": status}


def _notify_rule_change(rule_id: str, version: str) -> None:
    """通知已儲存模擬涉及此規則的使用者（保存的舊計算結果不會被改寫）。"""
    with service_session() as conn:
        users = rows(conn, """select distinct s.user_id::text from simulation_results r
                              join simulation_scenarios s on s.id = r.scenario_id
                              where r.rule_versions ? :k""", k=rule_id)
        for u in users:
            conn.execute(text("""insert into notifications (user_id, notification_type, category, title, message, dedupe_key)
                                 values (cast(:u as uuid), 'saved_scenario_rule_changed', 'real_regulation', :t, :m, :d)
                                 on conflict (user_id, dedupe_key) do nothing"""),
                         {"u": u["user_id"], "t": "你儲存的模擬所使用的規則已更新",
                          "m": f"規則 {rule_id} 版本 {version} 已啟用。舊的計算結果保留不變，可重新計算比較差異。",
                          "d": f"rule:{rule_id}@{version}"})


@router.get("/admin/review-queue", tags=["admin"])
def review_queue(user: Principal = Reviewer) -> dict:
    rules = [{"rule_id": rv.rule_id, "version": rv.version, "rule_name": rv.rule_name, "review_status": rv.review_status,
              "is_demo": rv.is_demo, "citation_validated": rv.citation_ok, "has_official_source": bool(rv.raw.get("sources")),
              "citations": [c.__dict__ for c in rv.citations], "parameters": rv.parameters,
              "plain_language": rv.plain_language}
             for rv in all_rule_versions(status_overrides()) if rv.review_status in ("pending_review", "approved", "draft")]
    with user_session(user.claims) as conn:
        ups = rows(conn, """select id::text, title, is_demo, review_status, detected_at::text from regulatory_updates
                            where review_status = 'pending_review' order by detected_at desc""")
    return {"rules": rules, "regulatory_updates": ups}


class UpdateReviewIn(BaseModel):
    decision: Literal["approve", "reject"]
    notes: str = Field("", max_length=2000)


@router.post("/admin/regulatory/{uid}/review", tags=["admin"])
def review_update(uid: str, body: UpdateReviewIn, request: Request, user: Principal = Reviewer) -> dict:
    status = "approved" if body.decision == "approve" else "rejected"
    with user_session(user.claims) as conn:
        r = one(conn, "update regulatory_updates set review_status = :s where id::text = :i returning is_demo, title",
                s=status, i=uid)
        if r is None:
            raise ApiError(404, "not_found", "找不到法規更新")
        conn.execute(text("""insert into reviews (reviewer_id, resource_type, resource_id, decision, notes)
                             values (auth.uid(), 'regulatory_update', cast(:i as uuid), :d, :n)"""),
                     {"i": uid, "d": body.decision, "n": body.notes})
    audit(request, user.id, f"regulatory_update.{body.decision}", "regulatory_update", uid)
    return {"id": uid, "review_status": status,
            "note": "示範更新只會標記審查結果，不會套用到正式規則" if r["is_demo"] else
                    "已核准的更新仍需建立新規則版本並經啟用後才會影響計算"}


@router.post("/admin/legal-sources/sync", tags=["admin"])
def sync_sources(request: Request, user: Principal = Admin) -> dict:
    """重新下載官方資料（需 LEGAL_SOURCE_SYNC_ENABLED=true），再比對資料庫版本、建立待審查更新。"""
    from ..core.config import get_settings
    fetched = False
    if get_settings().legal_source_sync_enabled:
        raw = ROOT / ".tmp" / f"legal_raw_{date.today().isoformat()}"
        subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "extract_legal_sources.py"), str(raw)],
                       check=True, timeout=300, capture_output=True)
        fetched = True
    result = check_for_updates()
    audit(request, user.id, "legal_sources.sync", "legal_document", None, {"fetched": fetched, **result})
    return {"fetched_from_official_sources": fetched, **result,
            "note": None if fetched else "未啟用 LEGAL_SOURCE_SYNC_ENABLED，只比對本機已下載的官方資料"}


@router.get("/admin/evaluation", tags=["admin"])
def evaluation(user: Principal = Reviewer) -> dict:
    """讀取最近一次評估結果（由 scripts/run_evaluation.py 產生）；沒有就回報 NOT RUN。"""
    p = ROOT / "data" / "evaluation" / "latest_results.json"
    if not p.exists():
        return {"status": "NOT RUN", "note": "尚未執行 scripts/run_evaluation.py"}
    return json.loads(p.read_text(encoding="utf-8"))


@router.get("/admin/system-health", tags=["admin"])
def system_health(user: Principal = Admin) -> dict:
    from .public import ready
    with service_session() as conn:
        counts = one(conn, """select (select count(*) from profiles)::int as users,
                                (select count(*) from legal_articles)::int as articles,
                                (select count(*) from legal_chunks where embedding is not null)::int as embedded_chunks,
                                (select count(*) from legal_chunks)::int as chunks,
                                (select count(*) from agent_runs where status = 'failed')::int as failed_runs,
                                (select count(*) from jobs where status in ('failed','dead'))::int as failed_jobs""")
    return {"ready": ready(), "counts": counts}


@router.get("/admin/audit-logs", tags=["admin"])
def audit_logs(user: Principal = Admin, limit: int = 100) -> dict:
    with user_session(user.claims) as conn:
        return {"items": rows(conn, """select id::text, actor_id::text, actor_type, action, resource_type, resource_id::text,
                                         metadata, request_id, created_at::text from audit_logs
                                       order by created_at desc limit :l""", l=max(1, min(limit, 500)))}


@router.get("/admin/users", tags=["admin"])
def users(user: Principal = Admin) -> dict:
    with service_session() as conn:
        return {"items": rows(conn, "select id::text, email, display_name, role, created_at::text from profiles order by created_at")}


@router.get("/admin/agent-config", tags=["admin"])
def agent_config(user: Principal = Admin) -> dict:
    from ..agents.llm import ping
    from ..agents.workflow import AGENTS
    from ..core.config import get_settings
    s = get_settings()
    return {"llm": ping(), "agents": [{"name": n, "description": d, "kind": k} for n, d, k in AGENTS],
            "limits": {"max_agent_iterations": s.max_agent_iterations, "max_analysis_cost": s.max_analysis_cost,
                       "llm_timeout_seconds": s.llm_timeout_seconds},
            "tool_allowlist": ["financial_engine.margin", "financial_engine.day_trading", "legal_rules.evaluate",
                               "legal_rag.search", "contracts.clauses"]}


@router.get("/admin/knowledge-base", tags=["admin"])
def knowledge(user: Principal = Reviewer) -> dict:
    from .public import documents
    with service_session() as conn:
        c = one(conn, """select count(*)::int as chunks, count(embedding)::int as embedded,
                           max(embedding_model) as model from legal_chunks""")
    return {"documents": documents()["items"], "chunks": c}


class GrantIn(BaseModel):
    grantee_email: str
    purpose: str = Field(..., min_length=4, max_length=300)
    hours: int = Field(24, ge=1, le=168)


@router.post("/contracts/{cid}/grants", tags=["contracts"])
def grant_access(cid: str, body: GrantIn, request: Request,
                 user: Principal = Depends(require_role("investor", "legal_reviewer", "system_admin"))) -> dict:
    """只有契約擁有者能授權他人（例如審查員）暫時讀取；管理員沒有預設讀取權。"""
    with service_session() as conn:
        g = one(conn, "select id::text from profiles where email = :e", e=body.grantee_email.strip().lower())
    if g is None:
        raise ApiError(404, "not_found", "找不到被授權的帳號")
    with user_session(user.claims) as conn:
        r = one(conn, """insert into contract_access_grants (contract_id, granted_by, grantee_id, purpose, expires_at)
                         select c.id, auth.uid(), cast(:g as uuid), :p, now() + make_interval(hours => :h)
                         from contracts c where c.id::text = :c and c.user_id = auth.uid() returning id::text""",
                g=g["id"], p=body.purpose, h=body.hours, c=cid)
    if r is None:
        raise ApiError(404, "not_found", "找不到契約")
    audit(request, user.id, "contract.grant", "contract", cid, {"grantee": g["id"], "hours": body.hours})
    return {"grant_id": r["id"]}


def _unused(_: Any) -> Path:  # pragma: no cover
    return Path()
