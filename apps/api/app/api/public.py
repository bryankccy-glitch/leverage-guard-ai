"""公開 API：健康檢查、登入、訪客試算、法規與規則查詢。訪客可試算但不保存任何資料。"""
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from ..agents import llm
from ..core.audit import audit
from ..core.config import get_settings
from ..core.db import one, rows, user_session
from ..core.errors import ApiError
from ..legal_rag.search import search as legal_search
from ..legal_rules.engine import all_rule_versions, evaluate
from ..scenario_engine.presets import presets
from ..schemas.calc import DayTradeCalcIn, MarginCalcIn, MarginScenarioIn, PortfolioCalcIn
from ..security.auth import DEMO_ACCOUNTS, MaybeUser, issue_local_token
from ..services import calc_service
from ..services.rule_status import status_overrides

router = APIRouter()


@router.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}


@router.get("/ready", tags=["system"])
def ready() -> dict:
    checks: dict = {}
    try:
        with user_session(None) as conn:
            checks["database"] = one(conn, "select count(*)::int as n from legal_articles")["n"] > 0
    except Exception:  # noqa: BLE001
        checks["database"] = False
    checks["storage"] = get_settings().storage_dir.parent.exists()
    checks["llm"] = llm.ping()
    ok = checks["database"]
    return {"status": "ok" if ok else "degraded", "checks": checks}


# ───── 驗證 ─────
class LoginIn(BaseModel):
    email: str = Field(..., max_length=200)


@router.get("/auth/config", tags=["auth"])
def auth_config() -> dict:
    s = get_settings()
    return {"mode": s.auth_mode, "demo_mode": s.demo_mode,
            "demo_accounts": [{"email": a["email"], "label": a["display_name"], "role": a["role"]}
                              for a in DEMO_ACCOUNTS] if s.auth_mode == "local" else [],
            "supabase_url": s.supabase_url if s.auth_mode == "supabase" else None,
            # anon key 本來就是公開金鑰（權限由 RLS 與後端控管），前端用它呼叫 Supabase Auth 帳號密碼登入
            "supabase_anon_key": s.supabase_anon_key if s.auth_mode == "supabase" else None,
            "login_domain": s.login_domain if s.auth_mode == "supabase" else None}


@router.post("/auth/dev/login", tags=["auth"])
def dev_login(body: LoginIn, request: Request) -> dict:
    if get_settings().auth_mode != "local":
        raise ApiError(404, "not_found", "本機登入未啟用")
    acc = next((a for a in DEMO_ACCOUNTS if a["email"] == body.email.strip().lower()), None)
    if acc is None:
        raise ApiError(401, "unauthorized", "只能使用示範帳號登入（本機模式）")
    token, ttl = issue_local_token(acc["id"], acc["email"])
    audit(request, acc["id"], "auth.login", "profile", acc["id"], {"mode": "local"})
    return {"access_token": token, "token_type": "bearer", "expires_in": ttl,
            "user": {"id": acc["id"], "email": acc["email"], "display_name": acc["display_name"], "role": acc["role"]}}


@router.get("/me", tags=["auth"])
def me(user: MaybeUser) -> dict:
    if user is None:
        return {"guest": True, "role": "guest"}
    with user_session(user.claims) as conn:
        p = one(conn, "select id::text, email, display_name, role, preferred_language, theme from profiles where id = auth.uid()")
    return {"guest": False, **(p or {})}


class ProfileIn(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=80)
    preferred_language: Literal["zh-TW", "en"] | None = None
    theme: Literal["light", "dark", "system"] | None = None


@router.patch("/me", tags=["auth"])
def update_me(body: ProfileIn, user: MaybeUser) -> dict:
    if user is None:
        raise ApiError(401, "unauthorized", "請先登入")
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if fields:
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        with user_session(user.claims) as conn:
            from sqlalchemy import text
            conn.execute(text(f"update profiles set {sets} where id = auth.uid()"), fields)  # noqa: S608 欄位名為白名單
    return me(user)


# ───── 計算（訪客可用） ─────
@router.post("/calculate/margin", tags=["calculate"])
def calc_margin(body: MarginCalcIn) -> dict:
    return calc_service.margin_calc(body, status_overrides())


@router.post("/calculate/day-trading", tags=["calculate"])
def calc_day_trading(body: DayTradeCalcIn) -> dict:
    return calc_service.day_trade_calc(body, status_overrides())


@router.post("/calculate/scenario", tags=["calculate"])
def calc_scenario(body: MarginScenarioIn) -> dict:
    return calc_service.margin_scenario(body, status_overrides())


@router.post("/calculate/portfolio", tags=["calculate"])
def calc_portfolio(body: PortfolioCalcIn) -> dict:
    return calc_service.portfolio_calc(body)


@router.get("/calculate/presets", tags=["calculate"])
def calc_presets() -> dict:
    return {"items": presets()}


# ───── 法規 ─────
@router.get("/legal/search", tags=["legal"])
def search(q: Annotated[str, Query(min_length=1, max_length=200)],
           mode: Literal["keyword", "semantic", "hybrid"] = "hybrid",
           trading_type: Literal["margin", "day_trading", "general"] | None = None,
           source_type: Literal["statute", "regulation", "exchange_rule"] | None = None,
           document: str | None = Query(None, max_length=40), limit: int = Query(10, ge=1, le=30)) -> dict:
    return legal_search(q, mode, limit, trading_type, source_type, document)


@router.get("/legal/documents", tags=["legal"])
def documents() -> dict:
    with user_session(None) as conn:
        items = rows(conn, """select d.id::text, d.source_key, d.official_title, d.authority, d.source_type, d.publisher,
                                d.trading_types, d.official_url, d.legal_status, v.version, v.retrieved_at, v.content_hash,
                                (select count(*) from legal_articles a where a.document_version_id = v.id)::int as article_count
                              from legal_documents d join legal_document_versions v on v.document_id = d.id and v.is_current
                              order by d.source_type, d.official_title""")
    for i in items:
        i["retrieved_at"] = str(i["retrieved_at"])
    return {"items": items}


@router.get("/legal/documents/{doc_id}", tags=["legal"])
def document(doc_id: str) -> dict:
    with user_session(None) as conn:
        d = one(conn, """select d.id::text, d.source_key, d.official_title, d.authority, d.source_type, d.official_url,
                           d.trading_types, d.legal_status, v.id::text as version_id, v.version, v.retrieved_at, v.content_hash
                         from legal_documents d join legal_document_versions v on v.document_id = d.id and v.is_current
                         where d.id::text = :i or d.source_key = :i""", i=doc_id)
        if d is None:
            raise ApiError(404, "not_found", "找不到法規")
        d["articles"] = rows(conn, """select id::text, article_number, chapter, article_content as content
                                      from legal_articles where document_version_id = :v order by sort_order""",
                             v=d["version_id"])
        d["versions"] = rows(conn, """select version, retrieved_at::text, content_hash, is_current from legal_document_versions
                                      where document_id = cast(:i as uuid) order by created_at desc""", i=d["id"])
    d["retrieved_at"] = str(d["retrieved_at"])
    return d


@router.get("/legal/articles/{article_id}", tags=["legal"])
def article(article_id: str) -> dict:
    with user_session(None) as conn:
        a = one(conn, """select a.id::text, a.article_number, a.chapter, a.article_content as content, d.official_title,
                           d.source_key, d.authority, d.official_url, v.version, v.retrieved_at::text
                         from legal_articles a join legal_document_versions v on v.id = a.document_version_id
                         join legal_documents d on d.id = v.document_id where a.id::text = :i""", i=article_id)
    if a is None:
        raise ApiError(404, "not_found", "找不到條文")
    return a


def _rights(kind: str, trading_type: str | None) -> list[dict]:
    out = []
    for rv in all_rule_versions(status_overrides()):
        if rv.is_demo and rv.raw.get("sources"):
            continue
        if trading_type and rv.trading_type not in (trading_type, "general"):
            continue
        for item in rv.raw.get(f"investor_{kind}") or []:
            out.append({"description": item, "rule_id": rv.rule_id, "rule_name": rv.rule_name,
                        "trading_type": rv.trading_type, "review_status": rv.review_status,
                        "plain_language": rv.plain_language, "citations": [c.__dict__ for c in rv.citations]})
    return out


@router.get("/legal/rights", tags=["legal"])
def rights(trading_type: Literal["margin", "day_trading", "general"] | None = None) -> dict:
    return {"items": _rights("rights", trading_type)}


@router.get("/legal/obligations", tags=["legal"])
def obligations(trading_type: Literal["margin", "day_trading", "general"] | None = None) -> dict:
    return {"items": _rights("obligations", trading_type)}


# ───── 規則 ─────
@router.get("/rules", tags=["rules"])
def rules_list(trading_type: str | None = None) -> dict:
    items = {}
    for rv in all_rule_versions(status_overrides()):
        if trading_type and rv.trading_type not in (trading_type, "general"):
            continue
        it = items.setdefault(rv.rule_id, {"rule_id": rv.rule_id, "rule_name": rv.rule_name, "rule_type": rv.rule_type,
                                           "trading_type": rv.trading_type, "versions": []})
        it["versions"].append({"version": rv.version, "review_status": rv.review_status, "is_demo": rv.is_demo,
                               "effective_from": str(rv.effective_from) if rv.effective_from else None,
                               "effective_to": str(rv.effective_to) if rv.effective_to else None,
                               "citation_validated": rv.citation_ok, "has_official_source": bool(rv.raw.get("sources"))})
    return {"items": list(items.values())}


@router.get("/rules/{rule_id}", tags=["rules"])
def rule_detail(rule_id: str) -> dict:
    versions = [rv for rv in all_rule_versions(status_overrides()) if rv.rule_id == rule_id]
    if not versions:
        raise ApiError(404, "not_found", "找不到規則")
    return {"rule_id": rule_id, "versions": [{
        "version": rv.version, "rule_name": rv.rule_name, "review_status": rv.review_status, "is_demo": rv.is_demo,
        "effective_from": str(rv.effective_from) if rv.effective_from else None,
        "effective_to": str(rv.effective_to) if rv.effective_to else None, "parameters": rv.parameters,
        "condition": rv.condition, "event": rv.event, "required_facts": rv.required_facts, "exceptions": rv.exceptions,
        "plain_language": rv.plain_language, "citations": [c.__dict__ for c in rv.citations],
        "definition": rv.raw} for rv in versions]}


@router.get("/rules/{rule_id}/versions", tags=["rules"])
def rule_versions(rule_id: str) -> dict:
    return rule_detail(rule_id)


class EvaluateIn(BaseModel):
    trading_type: Literal["margin", "day_trading", "general"]
    facts: dict
    as_of: date | None = None


@router.post("/rules/evaluate", tags=["rules"])
def rules_evaluate(body: EvaluateIn) -> dict:
    from ..financial_engine.types import serialize
    ev = evaluate(body.trading_type, body.facts, body.as_of or date.today(), status_overrides=status_overrides())
    return serialize(ev.__dict__)
