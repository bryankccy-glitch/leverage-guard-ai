"""登入使用者 API：模擬、數位分身、契約、Agent、Copilot、報告、通知、Dashboard。

所有查詢都在 user_session（RLS 生效）內執行；只有系統工作（Agent 背景執行、寫入 agent 紀錄）用 service_session。
"""
from __future__ import annotations

import asyncio
import json
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, File, Form, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from ..agents import copilot as copilot_agent
from ..agents import workflow
from ..contracts import service as contracts
from ..core.audit import audit
from ..core.config import get_settings
from ..core.db import one, rows, service_session, user_session
from ..core.errors import ApiError
from ..financial_engine.portfolio import PositionLine, account_ratio
from ..financial_engine.rounding import D
from ..financial_engine.types import serialize
from ..schemas.calc import DayTradeCalcIn, MarginScenarioIn
from ..security.auth import CurrentUser
from ..services import calc_service, reports
from ..services.rule_status import status_overrides

router = APIRouter()


def _jsonable(r: dict[str, Any] | None) -> dict[str, Any] | None:
    if r is None:
        return None
    return json.loads(json.dumps(r, default=str))


# ───── 模擬 ─────
class SimulationIn(BaseModel):
    scenario_name: str = Field(..., min_length=1, max_length=120)
    scenario_type: Literal["margin", "day_trading", "extreme"]
    input_parameters: dict[str, Any]
    preset_key: str | None = Field(None, max_length=40)
    account_id: str | None = None


def _run_calc(stype: str, params: dict[str, Any]) -> dict[str, Any]:
    if stype == "day_trading" or ("trade_date" in params and "direction" in params):
        return calc_service.day_trade_calc(DayTradeCalcIn(**params), status_overrides())
    return calc_service.margin_scenario(MarginScenarioIn(**params), status_overrides())


def _save_result(conn, scenario_id: str, params: dict[str, Any], r: dict[str, Any]) -> str:  # noqa: ANN001
    res = one(conn, """insert into simulation_results (scenario_id, calculation_version, rule_version_label, rule_versions,
                         input_hash, financial_result, legal_result, assumptions, warnings)
                       values (:s, :cv, :rv, cast(:rvs as jsonb), :h, cast(:f as jsonb), cast(:l as jsonb),
                         cast(:a as jsonb), cast(:w as jsonb)) returning id::text""",
              s=scenario_id, cv=r["calculation_version"], rv=r["rule_version"],
              rvs=json.dumps(r["rule_versions"]), h=workflow.input_hash(params),
              f=json.dumps({k: r.get(k) for k in ("opening", "states", "metrics", "parameters")}, ensure_ascii=False,
                           default=str),
              l=json.dumps({"timeline": r["timeline"], "rule_evaluation": r.get("rule_evaluation"),
                            "rules": r.get("rules")}, ensure_ascii=False, default=str),
              a=json.dumps(r["assumptions"], ensure_ascii=False), w=json.dumps(r["warnings"], ensure_ascii=False))
    for n in r["timeline"]:
        conn.execute(text("""insert into legal_events (simulation_result_id, rule_key, event_type, trigger_condition,
                             event_status, event_date, legal_basis, missing_facts)
                             values (:r, :k, :e, :t, :s, :d, cast(:b as jsonb), cast(:m as jsonb))"""),
                     {"r": res["id"], "k": (n["rule_ids"] or [None])[0], "e": n["event_type"],
                      "t": n["trigger_condition"], "s": n["status"], "d": n["date"],
                      "b": json.dumps(n["legal_basis"], ensure_ascii=False, default=str),
                      "m": json.dumps(n["uncertainty"], ensure_ascii=False)})
    conn.execute(text("update simulation_scenarios set status='calculated', rule_version_label=:v where id=:i"),
                 {"v": r["rule_version"], "i": scenario_id})
    return res["id"]


@router.post("/simulations", tags=["simulations"], status_code=201)
def create_simulation(body: SimulationIn, user: CurrentUser, request: Request) -> dict:
    r = _run_calc(body.scenario_type, body.input_parameters)  # 先驗證並計算，失敗就不建立
    with user_session(user.claims) as conn:
        s = one(conn, """insert into simulation_scenarios (user_id, account_id, scenario_name, scenario_type, preset_key,
                           input_parameters) values (auth.uid(), :a, :n, :t, :k, cast(:i as jsonb)) returning id::text""",
                a=body.account_id, n=body.scenario_name, t=body.scenario_type, k=body.preset_key,
                i=json.dumps(body.input_parameters, ensure_ascii=False))
        rid = _save_result(conn, s["id"], body.input_parameters, r)
    audit(request, user.id, "simulation.create", "simulation_scenario", s["id"], {"type": body.scenario_type})
    return {"id": s["id"], "result_id": rid, "result": r}


@router.get("/simulations", tags=["simulations"])
def list_simulations(user: CurrentUser, page: int = 1, page_size: int = 20) -> dict:
    page_size = max(1, min(page_size, 100))
    with user_session(user.claims) as conn:
        items = rows(conn, """select id::text, scenario_name, scenario_type, preset_key, status, rule_version_label,
                                is_demo, created_at::text from simulation_scenarios
                              where status <> 'archived' order by created_at desc limit :l offset :o""",
                     l=page_size, o=(max(page, 1) - 1) * page_size)
        total = one(conn, "select count(*)::int as n from simulation_scenarios where status <> 'archived'")["n"]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/simulations/{sid}", tags=["simulations"])
def get_simulation(sid: str, user: CurrentUser) -> dict:
    with user_session(user.claims) as conn:
        s = one(conn, """select id::text, scenario_name, scenario_type, preset_key, input_parameters, status,
                           rule_version_label, is_demo, created_at::text from simulation_scenarios where id::text = :i""", i=sid)
        if s is None:
            raise ApiError(404, "not_found", "找不到模擬情境")
        s["results"] = rows(conn, """select id::text, calculation_version, rule_version_label, created_at::text
                                     from simulation_results where scenario_id = cast(:i as uuid)
                                     order by created_at desc""", i=sid)
        latest = one(conn, """select financial_result, legal_result, assumptions, warnings, calculation_version,
                                rule_version_label, rule_versions from simulation_results where scenario_id = cast(:i as uuid)
                              order by created_at desc limit 1""", i=sid)
    s["latest"] = _jsonable(latest)
    return s


@router.post("/simulations/{sid}/calculate", tags=["simulations"])
def recalc(sid: str, user: CurrentUser, request: Request) -> dict:
    """用目前生效的規則重新計算；舊結果保留（歷史紀錄不可覆寫）。"""
    with user_session(user.claims) as conn:
        s = one(conn, "select scenario_type, input_parameters from simulation_scenarios where id::text = :i", i=sid)
        if s is None:
            raise ApiError(404, "not_found", "找不到模擬情境")
        r = _run_calc(s["scenario_type"], s["input_parameters"])
        rid = _save_result(conn, sid, s["input_parameters"], r)
    audit(request, user.id, "simulation.recalculate", "simulation_scenario", sid)
    return {"result_id": rid, "result": r}


@router.get("/simulations/{sid}/timeline", tags=["simulations"])
def sim_timeline(sid: str, user: CurrentUser) -> dict:
    s = get_simulation(sid, user)
    if not s["latest"]:
        raise ApiError(404, "not_found", "尚未計算")
    return {"timeline": s["latest"]["legal_result"]["timeline"]}


class CompareIn(BaseModel):
    other_ids: list[str] = Field(default_factory=list, max_length=4)
    rule_overrides: dict[str, str] | None = None


@router.post("/simulations/{sid}/compare", tags=["simulations"])
def compare(sid: str, body: CompareIn, user: CurrentUser) -> dict:
    base = get_simulation(sid, user)
    items = [{"id": sid, "name": base["scenario_name"], "result": base["latest"]}]
    for oid in body.other_ids:
        o = get_simulation(oid, user)
        items.append({"id": oid, "name": o["scenario_name"], "result": o["latest"]})
    if body.rule_overrides and base["scenario_type"] != "day_trading":
        params = {**base["input_parameters"], "rule_overrides": body.rule_overrides}
        r = calc_service.margin_scenario(MarginScenarioIn(**params), status_overrides())
        items.append({"id": f"{sid}:rules", "name": "同一情境（套用比較規則版本）",
                      "result": {"financial_result": {"states": r["states"], "opening": r["opening"]},
                                 "legal_result": {"timeline": r["timeline"]}, "rule_version_label": r["rule_version"]}})
    return {"items": items}


@router.post("/simulations/{sid}/explain", tags=["simulations"], status_code=202)
def explain(sid: str, user: CurrentUser, background: BackgroundTasks, contract_id: str | None = None) -> dict:
    s = get_simulation(sid, user)
    ttype = "day_trading" if s["scenario_type"] == "day_trading" else "margin"
    if contract_id:
        with user_session(user.claims) as conn:
            if not one(conn, "select id from contracts where id::text = :c", c=contract_id):
                raise ApiError(404, "not_found", "找不到契約")
    run_id, cached = workflow.create_run(user.id, "simulation_analysis",
                                         {"t": ttype, "p": s["input_parameters"], "c": contract_id,
                                          "rv": s["rule_version_label"]}, scenario_id=sid, contract_id=contract_id)
    if not cached:
        background.add_task(workflow.run_simulation_analysis, run_id, ttype, s["input_parameters"], contract_id,
                            status_overrides())
    return {"run_id": run_id, "cached": cached}


@router.delete("/simulations/{sid}", tags=["simulations"], status_code=204)
def delete_simulation(sid: str, user: CurrentUser, request: Request) -> Response:
    with user_session(user.claims) as conn:
        r = conn.execute(text("update simulation_scenarios set status='archived' where id::text = :i"), {"i": sid})
    if r.rowcount == 0:
        raise ApiError(404, "not_found", "找不到模擬情境")
    audit(request, user.id, "simulation.archive", "simulation_scenario", sid)
    return Response(status_code=204)


# ───── Agent ─────
class AgentRunIn(BaseModel):
    trading_type: Literal["margin", "day_trading"]
    input_parameters: dict[str, Any]
    contract_id: str | None = None


@router.post("/agents/run", tags=["agents"], status_code=202)
def agents_run(body: AgentRunIn, user: CurrentUser, background: BackgroundTasks) -> dict:
    _run_calc(body.trading_type, body.input_parameters)  # 先驗證輸入
    run_id, cached = workflow.create_run(user.id, "simulation_analysis",
                                         {"t": body.trading_type, "p": body.input_parameters, "c": body.contract_id},
                                         contract_id=body.contract_id)
    if not cached:
        background.add_task(workflow.run_simulation_analysis, run_id, body.trading_type, body.input_parameters,
                            body.contract_id, status_overrides())
    return {"run_id": run_id, "cached": cached}


@router.get("/agents", tags=["agents"])
def agents_list(user: CurrentUser) -> dict:
    from ..agents.llm import provider_info
    info = provider_info()
    with user_session(user.claims) as conn:
        stats = {r["agent_name"]: r for r in rows(conn, """
            select agent_name, count(*)::int as executions,
              avg(duration_ms)::int as avg_duration_ms, sum(tokens)::int as tokens,
              (100.0 * sum(case when status = 'completed' then 1 else 0 end) / greatest(count(*), 1))::numeric(5,1) as success_rate,
              max(started_at)::text as last_run
            from agent_tasks group by agent_name""")}
    out = []
    for name, desc, kind in workflow.AGENTS:
        s = stats.get(name, {})
        out.append({"name": name, "description": desc, "kind": kind,
                    "model": info["model"] if kind in ("llm", "hybrid") else None,
                    "provider": info["provider"] if kind in ("llm", "hybrid") else "deterministic",
                    "executions": s.get("executions", 0), "success_rate": str(s.get("success_rate", "0")),
                    "avg_duration_ms": s.get("avg_duration_ms"), "token_usage": s.get("tokens", 0),
                    "estimated_cost": "0（本機模型）" if info["provider"] == "ollama" else None,
                    "last_run": s.get("last_run")})
    return {"items": out, "provider": info}


@router.get("/agents/runs", tags=["agents"])
def agent_runs(user: CurrentUser, limit: int = 20) -> dict:
    with user_session(user.claims) as conn:
        items = rows(conn, """select id::text, workflow_name, status, provider, model, total_tokens, created_at::text,
                                started_at::text, completed_at::text, error_message from agent_runs
                              order by created_at desc limit :l""", l=max(1, min(limit, 100)))
    return {"items": items}


@router.get("/agents/runs/{rid}", tags=["agents"])
def agent_run(rid: str, user: CurrentUser) -> dict:
    with user_session(user.claims) as conn:
        r = one(conn, """select id::text, workflow_name, status, provider, model, total_tokens, estimated_cost::text,
                           created_at::text, started_at::text, completed_at::text, error_message, output, scenario_id::text
                         from agent_runs where id::text = :i""", i=rid)
        if r is None:
            raise ApiError(404, "not_found", "找不到執行紀錄")
        r["tasks"] = rows(conn, """select id::text, agent_name, task_type, status, depends_on, output_summary, tool_calls,
                                     retrieved_sources, validation_result, tokens, error_message, started_at::text,
                                     finished_at::text, duration_ms from agent_tasks where agent_run_id = cast(:i as uuid)
                                   order by started_at""", i=rid)
    return _jsonable(r)


@router.get("/agents/runs/{rid}/events", tags=["agents"])
async def agent_events(rid: str, user: CurrentUser, request: Request, after: int = 0) -> StreamingResponse:
    with user_session(user.claims) as conn:
        if not one(conn, "select id from agent_runs where id::text = :i", i=rid):
            raise ApiError(404, "not_found", "找不到執行紀錄")

    async def gen():
        last = after
        for _ in range(900):
            if await request.is_disconnected():
                return
            with user_session(user.claims) as conn:
                evs = rows(conn, """select seq, agent_name, status, message, created_at::text from agent_events
                                    where agent_run_id = cast(:i as uuid) and seq > :s order by seq""", i=rid, s=last)
                st = one(conn, "select status from agent_runs where id::text = :i", i=rid)
            for e in evs:
                last = e["seq"]
                yield f"event: progress\ndata: {json.dumps(e, ensure_ascii=False)}\n\n"
            if st and st["status"] in ("completed", "failed", "cancelled"):
                yield f"event: done\ndata: {json.dumps({'status': st['status']})}\n\n"
                return
            await asyncio.sleep(0.6)
    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/agents/runs/{rid}/cancel", tags=["agents"])
def cancel_run(rid: str, user: CurrentUser) -> dict:
    with user_session(user.claims) as conn:
        r = conn.execute(text("""update agent_runs set status='cancelled', completed_at=now() where id::text = :i
                                 and status in ('queued','running')"""), {"i": rid})
    return {"cancelled": r.rowcount > 0}


@router.post("/agents/runs/{rid}/retry", tags=["agents"], status_code=202)
def retry_run(rid: str, user: CurrentUser, background: BackgroundTasks) -> dict:
    r = agent_run(rid, user)
    if r["status"] not in ("failed", "cancelled"):
        raise ApiError(409, "conflict", "只有失敗或取消的執行可以重試")
    if not r.get("scenario_id"):
        raise ApiError(409, "conflict", "這筆執行沒有對應的模擬情境，請重新送出分析")
    return explain(r["scenario_id"], user, background)


# ───── Copilot ─────
class CopilotIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    context: dict[str, Any] | None = None
    scenario_id: str | None = None


@router.post("/copilot/messages", tags=["copilot"])
def copilot(body: CopilotIn, user: CurrentUser) -> dict:
    out = copilot_agent.answer(body.message, body.context)
    with user_session(user.claims) as conn:
        for role, content, payload in (("user", body.message, {}), ("assistant", out["answer"], out)):
            conn.execute(text("""insert into copilot_messages (user_id, scenario_id, role, content, payload)
                                 values (auth.uid(), :s, :r, :c, cast(:p as jsonb))"""),
                         {"s": body.scenario_id, "r": role, "c": content,
                          "p": json.dumps(payload, ensure_ascii=False, default=str)})
    return out


@router.post("/copilot/guest", tags=["copilot"])
def copilot_guest(body: CopilotIn) -> dict:
    """訪客版：不保存對話。"""
    return copilot_agent.answer(body.message, body.context)


# ───── 數位分身 ─────
class AccountIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    account_type: Literal["cash", "margin", "day_trading", "portfolio"]
    cash_balance: str = "0"


class PositionIn(BaseModel):
    asset_label: str = Field(..., min_length=1, max_length=60)
    trading_type: Literal["cash", "margin", "day_trading"] = "margin"
    quantity: str
    entry_price: str
    simulated_price: str
    financing_ratio: str | None = "0.6"
    interest_rate: str | None = None
    trading_date: date | None = None


class PositionPatch(BaseModel):
    simulated_price: str | None = None
    quantity: str | None = None
    financing_principal: str | None = None


def _account_state(conn, aid: str) -> dict[str, Any]:  # noqa: ANN001
    acc = one(conn, """select id::text, name, account_type, cash_balance::text, currency, is_simulation, created_at::text
                       from virtual_accounts where id::text = :i""", i=aid)
    if acc is None:
        raise ApiError(404, "not_found", "找不到虛擬帳戶")
    pos = rows(conn, """select id::text, asset_label, trading_type, quantity::text, entry_price::text, simulated_price::text,
                          financing_principal::text, financing_ratio::text, interest_rate::text, trading_date::text
                        from virtual_positions where account_id = cast(:i as uuid) order by created_at""", i=aid)
    col = rows(conn, """select id::text, asset_type, quantity::text, valuation::text, applicable_haircut::text
                        from collateral_assets where account_id = cast(:i as uuid)""", i=aid)
    margin_pos = [p for p in pos if p["trading_type"] == "margin" and D(p["financing_principal"]) > 0]
    fin = None
    if margin_pos:
        cval = sum((D(c["valuation"]) * (D(c["applicable_haircut"]) if c["applicable_haircut"] else D("1"))
                    for c in col), D("0"))
        fin = serialize(account_ratio([PositionLine(p["asset_label"], D(p["quantity"]), D(p["simulated_price"]),
                                                    D(p["financing_principal"])) for p in margin_pos], cval))
    mv = sum((D(p["quantity"]) * D(p["simulated_price"]) for p in pos), D("0"))
    cost = sum((D(p["quantity"]) * D(p["entry_price"]) for p in pos), D("0"))
    debt = sum((D(p["financing_principal"]) for p in pos), D("0"))
    return {**acc, "positions": pos, "collateral": col, "is_simulation": True,
            "financial_state": {"market_value": str(mv), "borrowed": str(debt), "own_equity": str(mv - debt),
                                "unrealized_pnl": str(mv - cost), "account_ratio": fin},
            "label": "Simulation 模擬資料"}


@router.get("/accounts", tags=["digital-twin"])
def accounts(user: CurrentUser) -> dict:
    with user_session(user.claims) as conn:
        ids = [r["id"] for r in rows(conn, "select id::text from virtual_accounts order by created_at")]
        return {"items": [_account_state(conn, i) for i in ids]}


@router.post("/accounts", tags=["digital-twin"], status_code=201)
def create_account(body: AccountIn, user: CurrentUser, request: Request) -> dict:
    with user_session(user.claims) as conn:
        a = one(conn, """insert into virtual_accounts (user_id, name, account_type, cash_balance)
                         values (auth.uid(), :n, :t, :c) returning id::text""", n=body.name, t=body.account_type,
                c=str(D(body.cash_balance)))
        out = _account_state(conn, a["id"])
    audit(request, user.id, "account.create", "virtual_account", a["id"])
    return out


@router.get("/accounts/{aid}", tags=["digital-twin"])
def get_account(aid: str, user: CurrentUser) -> dict:
    with user_session(user.claims) as conn:
        return _account_state(conn, aid)


@router.patch("/accounts/{aid}", tags=["digital-twin"])
def patch_account(aid: str, body: AccountIn, user: CurrentUser) -> dict:
    with user_session(user.claims) as conn:
        conn.execute(text("update virtual_accounts set name=:n, cash_balance=:c where id::text=:i"),
                     {"n": body.name, "c": str(D(body.cash_balance)), "i": aid})
        return _account_state(conn, aid)


@router.post("/accounts/{aid}/positions", tags=["digital-twin"], status_code=201)
def add_position(aid: str, body: PositionIn, user: CurrentUser) -> dict:
    q, ep = D(body.quantity), D(body.entry_price)
    ratio = D(body.financing_ratio) if body.trading_type == "margin" and body.financing_ratio else None
    fin = (q * ep * ratio).quantize(D("1")) if ratio else D("0")
    with user_session(user.claims) as conn:
        conn.execute(text("""insert into virtual_positions (account_id, asset_label, trading_type, quantity, entry_price,
                             simulated_price, financing_principal, financing_ratio, interest_rate, trading_date)
                             values (cast(:a as uuid), :l, :t, :q, :e, :s, :f, :r, :ir, coalesce(:d, current_date))"""),
                     {"a": aid, "l": body.asset_label, "t": body.trading_type, "q": str(q), "e": str(ep),
                      "s": str(D(body.simulated_price)), "f": str(fin), "r": str(ratio) if ratio else None,
                      "ir": body.interest_rate, "d": body.trading_date})
        return _account_state(conn, aid)


@router.patch("/positions/{pid}", tags=["digital-twin"])
def patch_position(pid: str, body: PositionPatch, user: CurrentUser) -> dict:
    fields = {k: str(D(v)) for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise ApiError(422, "validation_error", "沒有要更新的欄位")
    with user_session(user.claims) as conn:
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        r = one(conn, f"update virtual_positions set {sets} where id::text = :i returning account_id::text",  # noqa: S608
                **fields, i=pid)
        if r is None:
            raise ApiError(404, "not_found", "找不到部位")
        return _account_state(conn, r["account_id"])


@router.delete("/positions/{pid}", tags=["digital-twin"])
def delete_position(pid: str, user: CurrentUser) -> dict:
    with user_session(user.claims) as conn:
        r = one(conn, "delete from virtual_positions where id::text = :i returning account_id::text", i=pid)
        if r is None:
            raise ApiError(404, "not_found", "找不到部位")
        return _account_state(conn, r["account_id"])


# ───── 契約 ─────
@router.post("/contracts/upload", tags=["contracts"], status_code=201)
async def upload_contract(request: Request, user: CurrentUser, file: UploadFile = File(...),
                          broker_name: str | None = Form(None), acknowledge_privacy: bool = Form(False)) -> dict:
    if not acknowledge_privacy:
        raise ApiError(422, "validation_error", "請先確認隱私提醒（遮罩身分證字號、帳號、地址、電話、簽名）")
    data = await file.read(get_settings().max_upload_size + 1)
    if len(data) > get_settings().max_upload_size:
        raise ApiError(413, "payload_too_large", "檔案超過大小上限")
    if not data:
        raise ApiError(422, "validation_error", "檔案是空的")
    mime = contracts.sniff(data, file.filename or "")
    if mime is None:
        raise ApiError(415, "unsupported_media_type", "只接受 PDF、PNG、JPEG 或 UTF-8 純文字檔")
    rel, h = contracts.store(user.id, data)
    name = (file.filename or "contract")[:120]
    with user_session(user.claims) as conn:
        c = one(conn, """insert into contracts (user_id, document_name, broker_name, storage_path, mime_type, size_bytes,
                           document_hash) values (auth.uid(), :n, :b, :p, :m, :s, :h) returning id::text""",
                n=name, b=broker_name, p=rel, m=mime, s=len(data), h=h)
    audit(request, user.id, "contract.upload", "contract", c["id"], {"mime": mime, "size": len(data)})
    return {"id": c["id"], "document_hash": h, "mime_type": mime}


@router.get("/contracts", tags=["contracts"])
def list_contracts(user: CurrentUser) -> dict:
    with user_session(user.claims) as conn:
        return {"items": rows(conn, """select id::text, document_name, broker_name, mime_type, size_bytes, document_hash,
                                         status, is_demo, uploaded_at::text from contracts where user_id = auth.uid()
                                       order by uploaded_at desc""")}


@router.get("/contracts/{cid}", tags=["contracts"])
def get_contract(cid: str, user: CurrentUser, request: Request) -> dict:
    with user_session(user.claims) as conn:
        c = one(conn, """select id::text, user_id::text, document_name, broker_name, mime_type, size_bytes, document_hash,
                           page_count, status, is_demo, uploaded_at::text from contracts where id::text = :i""", i=cid)
        if c is None:
            raise ApiError(404, "not_found", "找不到契約")
        c["clauses"] = rows(conn, """select id::text, clause_number, page_number, char_start, char_end, original_text,
                                       category, extracted_parameters, verification_status from contract_clauses
                                     where contract_id = cast(:i as uuid) order by page_number, char_start""", i=cid)
        a = one(conn, """select analysis_result, provider, model_version, review_status, created_at::text
                         from contract_analyses where contract_id = cast(:i as uuid) order by created_at desc limit 1""", i=cid)
    if c["user_id"] != user.id:
        audit(request, user.id, "contract.read_by_grant", "contract", cid)
    c["analysis"] = _jsonable(a)
    c["download_url"] = f"/api/v1/contracts/{cid}/file?sig={contracts.sign(cid)}"
    return c


@router.get("/contracts/{cid}/file", tags=["contracts"])
def contract_file(cid: str, sig: str) -> Response:
    if not contracts.verify_sig(cid, sig):
        raise ApiError(403, "forbidden", "下載連結無效或已過期")
    with service_session() as conn:
        c = one(conn, "select storage_path, mime_type, document_name from contracts where id::text = :i", i=cid)
    if c is None:
        raise ApiError(404, "not_found", "找不到契約")
    data = contracts.storage_path(c["storage_path"]).read_bytes()
    return Response(data, media_type=c["mime_type"], headers={"Content-Disposition": "inline",
                                                              "Cache-Control": "private, no-store"})


def analyze_contract_now(cid: str, user_id: str) -> None:
    """兩階段：先寫入確定性條款切分（幾秒內可看），再呼叫 LLM 補白話說明。"""
    with service_session() as conn:
        c = one(conn, "select storage_path, mime_type from contracts where id::text = :i and user_id::text = :u",
                i=cid, u=user_id)
        conn.execute(text("update contracts set status='analyzing' where id::text = :i"), {"i": cid})
    try:
        data = contracts.storage_path(c["storage_path"]).read_bytes()
        pages, notes = contracts.extract_pages(data, c["mime_type"])
        has_text = any(p.strip() for p in pages)
        base = contracts.deterministic(pages) if has_text else {"clauses": [], "not_found_categories": [], "pii_redacted": {}}
        with service_session() as conn:
            conn.execute(text("delete from contract_clauses where contract_id = cast(:i as uuid)"), {"i": cid})
            for cl in base["clauses"]:
                conn.execute(text("""insert into contract_clauses (contract_id, clause_number, page_number, char_start, char_end,
                                     original_text, category, extracted_parameters, verification_status)
                                     values (cast(:c as uuid), :n, :p, :s, :e, :t, :cat, cast(:x as jsonb), 'verified_in_document')"""),
                             {"c": cid, "n": cl["clause_number"], "p": cl["page_number"], "s": cl["char_start"],
                              "e": cl["char_end"], "t": cl["original_text"], "cat": cl["category"],
                              "x": json.dumps(cl["extracted_parameters"], ensure_ascii=False)})
            conn.execute(text("update contracts set page_count=:p where id::text = :i"), {"p": len(pages), "i": cid})
        if has_text:
            ai = contracts.ai_notes(pages)
        else:
            ai = {"ai_clauses": [], "provider": "none", "model": None, "note": "；".join(notes), "pending_questions": [],
                  "document_type": "unknown"}
        summary = {**ai, "not_found_categories": base["not_found_categories"], "pii_redacted": base["pii_redacted"],
                   "extraction_notes": notes}
        with service_session() as conn:
            conn.execute(text("""insert into contract_analyses (contract_id, analysis_result, provider, model_version)
                                 values (cast(:c as uuid), cast(:r as jsonb), :p, :m)"""),
                         {"c": cid, "r": json.dumps(summary, ensure_ascii=False, default=str),
                          "p": ai.get("provider") or "none", "m": ai.get("model")})
            conn.execute(text("update contracts set status='analyzed' where id::text = :i"), {"i": cid})
            conn.execute(text("""insert into notifications (user_id, notification_type, category, title, message,
                                 resource_type, resource_id) values (cast(:u as uuid), 'contract_analysis_completed', 'system',
                                 '契約分析完成', :m, 'contract', cast(:c as uuid))"""),
                         {"u": user_id, "m": f"擷取 {len(base['clauses'])} 條條款", "c": cid})
    except Exception as e:  # noqa: BLE001
        with service_session() as conn:
            conn.execute(text("update contracts set status='failed' where id::text = :i"), {"i": cid})
        raise e


@router.post("/contracts/{cid}/analyze", tags=["contracts"], status_code=202)
def analyze_contract(cid: str, user: CurrentUser, background: BackgroundTasks, request: Request) -> dict:
    with user_session(user.claims) as conn:
        if not one(conn, "select id from contracts where id::text = :i and user_id = auth.uid()", i=cid):
            raise ApiError(404, "not_found", "找不到契約")
    background.add_task(analyze_contract_now, cid, user.id)
    audit(request, user.id, "contract.analyze", "contract", cid)
    return {"status": "analyzing"}


class ContractCompareIn(BaseModel):
    contract_ids: list[str] = Field(..., min_length=2, max_length=4)


@router.post("/contracts/compare", tags=["contracts"])
def compare_contracts(body: ContractCompareIn, user: CurrentUser) -> dict:
    analyses = []
    for cid in body.contract_ids:
        c = get_contract(cid, user, None)  # type: ignore[arg-type]
        analyses.append({"contract_id": cid, "document_name": c["document_name"], "clauses": c["clauses"]})
    return {"rows": contracts.compare(analyses), "note": "本比較只列出文件中的原始條款，不推薦任何證券商。"}


@router.delete("/contracts/{cid}", tags=["contracts"], status_code=204)
def delete_contract(cid: str, user: CurrentUser, request: Request) -> Response:
    with user_session(user.claims) as conn:
        c = one(conn, "delete from contracts where id::text = :i and user_id = auth.uid() returning storage_path", i=cid)
    if c is None:
        raise ApiError(404, "not_found", "找不到契約")
    with service_session() as conn:
        still = one(conn, "select 1 as x from contracts where storage_path = :p", p=c["storage_path"])
    if not still:
        contracts.storage_path(c["storage_path"]).unlink(missing_ok=True)
    audit(request, user.id, "contract.delete", "contract", cid)
    return Response(status_code=204)


@router.post("/contracts/demo", tags=["contracts"], status_code=201)
def add_demo_contract(user: CurrentUser, background: BackgroundTasks) -> dict:
    from ..services.demo_data import demo_contract_pdf
    data = demo_contract_pdf()
    rel, h = contracts.store(user.id, data)
    with user_session(user.claims) as conn:
        c = one(conn, """insert into contracts (user_id, document_name, broker_name, storage_path, mime_type, size_bytes,
                           document_hash, is_demo) values (auth.uid(), '虛構示範融資融券契約.pdf', '示範證券（虛構）', :p,
                           'application/pdf', :s, :h, true) returning id::text""", p=rel, s=len(data), h=h)
    background.add_task(analyze_contract_now, c["id"], user.id)
    return {"id": c["id"]}


# ───── 報告 ─────
class ReportIn(BaseModel):
    run_id: str
    report_type: Literal["investor", "professional"] = "investor"


@router.post("/reports", tags=["reports"], status_code=201)
def create_report(body: ReportIn, user: CurrentUser, request: Request) -> dict:
    run = agent_run(body.run_id, user)
    if run["status"] != "completed" or not run.get("output"):
        raise ApiError(409, "conflict", "分析尚未完成，無法產生報告")
    content = reports.build(body.report_type, run["output"])
    out = run["output"]
    with user_session(user.claims) as conn:
        r = one(conn, """insert into reports (user_id, scenario_id, report_type, report_content, calculation_version,
                           rule_version, legal_source_version, model_version)
                         values (auth.uid(), :s, :t, cast(:c as jsonb), :cv, :rv, :lv, :mv)
                         returning id::text, report_number, created_at::text""",
                s=run.get("scenario_id"), t=body.report_type, c=json.dumps(content, ensure_ascii=False, default=str),
                cv=out["calculation_version"], rv=out["rule_version"], lv=out.get("legal_source_version") or "",
                mv=f"{out['explanation_provider']}:{out.get('explanation_model')}")
    # 通知屬於系統動作：使用者沒有新增通知的 RLS 權限，改用 service_session
    with service_session() as conn:
        conn.execute(text("""insert into notifications (user_id, notification_type, category, title, message, resource_type,
                             resource_id) values (cast(:u as uuid), 'report_generated', 'system', '報告已產生', :m, 'report',
                             cast(:i as uuid))"""), {"u": user.id, "m": r["report_number"], "i": r["id"]})
    audit(request, user.id, "report.create", "report", r["id"], {"type": body.report_type})
    return {"id": r["id"], "report_number": r["report_number"]}


@router.get("/reports", tags=["reports"])
def list_reports(user: CurrentUser) -> dict:
    with user_session(user.claims) as conn:
        return {"items": rows(conn, """select id::text, report_number, report_type, calculation_version, rule_version,
                                         review_status, created_at::text from reports order by created_at desc""")}


@router.get("/reports/{rid}", tags=["reports"])
def get_report(rid: str, user: CurrentUser) -> dict:
    with user_session(user.claims) as conn:
        r = one(conn, """select id::text, report_number, report_type, report_content, calculation_version, rule_version,
                           legal_source_version, model_version, review_status, created_at::text, scenario_id::text
                         from reports where id::text = :i""", i=rid)
    if r is None:
        raise ApiError(404, "not_found", "找不到報告")
    return _jsonable(r)


@router.get("/reports/{rid}/export", tags=["reports"])
def export_report(rid: str, user: CurrentUser, format: Literal["pdf", "json", "csv"] = "pdf") -> Response:  # noqa: A002
    r = get_report(rid, user)
    meta = {"report_number": r["report_number"], "generated_at": r["created_at"],
            "calculation_version": r["calculation_version"], "rule_version": r["rule_version"],
            "legal_source_version": r["legal_source_version"], "model_version": r["model_version"]}
    fname = f"{r['report_number']}.{format}"
    if format == "json":
        return Response(json.dumps({"meta": meta, **r["report_content"]}, ensure_ascii=False, indent=1),
                        media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{fname}"'})
    if format == "csv":
        return Response("﻿" + reports.to_csv(r["report_content"]), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{fname}"'})
    curve = None
    if r["report_content"].get("trading_type") == "margin" and r.get("scenario_id"):
        s = get_simulation(r["scenario_id"], user)
        p = s["input_parameters"]
        from ..schemas.calc import MarginCalcIn
        curve = calc_service.margin_calc(MarginCalcIn(asset_label=p.get("asset_label", "模擬資產"),
                                                      buy_price=p["buy_price"], quantity=p["quantity"],
                                                      financing_ratio=p.get("financing_ratio", "0.6"),
                                                      current_price=p["buy_price"]))["curve"]
    pdf = reports.to_pdf(r["report_content"], meta, curve)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{fname}"'})


# ───── 通知、Dashboard、紀錄 ─────
@router.get("/notifications", tags=["notifications"])
def notifications(user: CurrentUser, unread: bool = False) -> dict:
    with user_session(user.claims) as conn:
        items = rows(conn, f"""select id::text, notification_type, category, title, message, resource_type,
                                resource_id::text, read_at::text, created_at::text from notifications
                              {'where read_at is null' if unread else ''} order by created_at desc limit 100""")
    return {"items": items}


@router.patch("/notifications/{nid}/read", tags=["notifications"])
def mark_read(nid: str, user: CurrentUser) -> dict:
    with user_session(user.claims) as conn:
        conn.execute(text("update notifications set read_at = now() where id::text = :i and read_at is null"), {"i": nid})
    return {"ok": True}


@router.post("/notifications/read-all", tags=["notifications"])
def mark_all(user: CurrentUser) -> dict:
    with user_session(user.claims) as conn:
        conn.execute(text("update notifications set read_at = now() where read_at is null"))
    return {"ok": True}


class SubscriptionIn(BaseModel):
    topics: list[Literal["margin_rules", "day_trading_rules", "legal_document", "saved_scenario_rules"]]
    digest: bool = False


@router.get("/notifications/subscriptions", tags=["notifications"])
def subs(user: CurrentUser) -> dict:
    with user_session(user.claims) as conn:
        return {"items": rows(conn, "select topic, target, digest from notification_subscriptions")}


@router.put("/notifications/subscriptions", tags=["notifications"])
def set_subs(body: SubscriptionIn, user: CurrentUser) -> dict:
    with user_session(user.claims) as conn:
        conn.execute(text("delete from notification_subscriptions where user_id = auth.uid()"))
        for t in set(body.topics):
            conn.execute(text("""insert into notification_subscriptions (user_id, topic, digest)
                                 values (auth.uid(), :t, :d)"""), {"t": t, "d": body.digest})
    return subs(user)


@router.get("/dashboard", tags=["dashboard"])
def dashboard(user: CurrentUser) -> dict:
    with user_session(user.claims) as conn:
        k = one(conn, """select
            (select count(*) from simulation_scenarios where status <> 'archived')::int as scenarios,
            (select count(*) from contracts where user_id = auth.uid() and status = 'analyzed')::int as contracts,
            (select count(*) from reports)::int as reports,
            (select count(*) from regulatory_updates where detected_at > now() - interval '90 days')::int as reg_updates,
            (select count(*) from notifications where read_at is null)::int as unread""")
        recent = rows(conn, """select id::text, scenario_name, scenario_type, status, rule_version_label, is_demo,
                                 created_at::text from simulation_scenarios where status <> 'archived'
                               order by created_at desc limit 6""")
        latest = """r.id in (select distinct on (scenario_id) id from simulation_results order by scenario_id, created_at desc)
                    and s.status <> 'archived' and e.event_type <> 'price_change'"""
        pending = rows(conn, f"""select e.event_type, e.event_status, e.trigger_condition, s.scenario_name, s.id::text as scenario_id
                                from legal_events e join simulation_results r on r.id = e.simulation_result_id
                                join simulation_scenarios s on s.id = r.scenario_id
                                where e.event_status in ('requires_confirmation','triggered_in_simulation') and {latest}
                                order by (e.event_status = 'requires_confirmation') desc, r.created_at desc limit 12""")
        status_counts = {r["event_status"]: r["n"] for r in rows(conn, f"""
            select e.event_status, count(*)::int as n from legal_events e
            join simulation_results r on r.id = e.simulation_result_id join simulation_scenarios s on s.id = r.scenario_id
            where {latest} group by e.event_status""")}
        updates = rows(conn, """select id::text, title, authority, review_status, is_demo, effective_date::text, detected_at::text
                                from regulatory_updates order by detected_at desc limit 5""")
        accs = [r["id"] for r in rows(conn, "select id::text from virtual_accounts order by created_at limit 1")]
        account = _account_state(conn, accs[0]) if accs else None
        runs = rows(conn, "select status, count(*)::int as n from agent_runs group by status")
    return {"kpis": {**k, "pending_legal_items": status_counts.get("requires_confirmation", 0)},
            "event_status_counts": status_counts, "recent_simulations": recent,
            "risk_overview": pending, "regulatory_updates": updates, "account": account,
            "agent_runs": {r["status"]: r["n"] for r in runs}, "is_simulation": True}


@router.get("/history", tags=["dashboard"])
def history(user: CurrentUser) -> dict:
    with user_session(user.claims) as conn:
        return {"items": rows(conn, """select r.id::text, s.id::text as scenario_id, s.scenario_name, s.scenario_type,
                                         r.calculation_version, r.rule_version_label, r.created_at::text
                                       from simulation_results r join simulation_scenarios s on s.id = r.scenario_id
                                       order by r.created_at desc limit 100""")}
