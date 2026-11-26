"""多代理分析工作流程（Orchestrator 管理 Agent 依賴、重試、預算，並把每一步寫入 agent_tasks / agent_events）。

Agent 與執行方式：
  orchestrator            確定性：規劃步驟、預算、合併結果
  financial_calculation   確定性：呼叫金融計算引擎（不使用 LLM 計算數字）
  legal_rules             確定性：呼叫規則引擎
  legal_retrieval         確定性＋檢索：依觸發事件查法規
  contract                確定性：取出使用者契約中相關的原始條款
  verification            確定性：引用、版本、數字一致性
  plain_language          LLM（千問／Gemini）；不可用時用規則模板並標示
  review                  確定性：買賣建議、未驗證數字、個資
  report                  確定性：組成最終結構化輸出
（scenario 用在 Copilot 解析自然語言；regulatory_watch 用在法規監察工作流程）

前端看到的進度來自 agent_events 資料列，是真實執行紀錄，不是預先寫好的動畫。
"""
from __future__ import annotations

import hashlib
import json
import time
import traceback
from datetime import date
from typing import Any

from sqlalchemy import text

from .. import i18n
from ..core.config import get_settings
from ..core.db import one, rows, service_session
from ..legal_rag.search import search as legal_search
from . import llm
from .guards import advice_violations, misconceptions, redact_pii, unverified_numbers
from .schemas import AIExplanation

PROMPT_VERSION = "explain-v3"

AGENTS = [
    ("orchestrator", "規劃工作流程、管理依賴、預算與重試、整合輸出", "deterministic"),
    ("financial_calculation", "驗證輸入並呼叫金融計算引擎，不以 LLM 計算數字", "deterministic"),
    ("scenario", "把自然語言假設轉成結構化情境參數並呼叫情境引擎", "hybrid"),
    ("legal_retrieval", "依交易情境檢索相關法規條文與官方來源", "deterministic"),
    ("legal_rules", "呼叫 Regulation-as-Code 規則引擎，找出法律事件與缺少的事實", "deterministic"),
    ("contract", "取出使用者契約中的相關原始條款", "hybrid"),
    ("regulatory_watch", "比較官方法規新舊版本，建立待審查的規則更新", "deterministic"),
    ("verification", "驗證引用、規則版本與計算結果一致性", "deterministic"),
    ("plain_language", "把金融與法律結果轉成白話繁體中文，保留條件與不確定性", "llm"),
    ("review", "檢查買賣建議、未驗證數字、個資與事實推論混淆", "deterministic"),
    ("report", "整合計算、法規、契約與時間軸，產生結構化結果", "deterministic"),
]
EVENT_QUERIES = {
    "maintenance_threshold_breach": "擔保維持率 低於 補繳", "top_up_deadline": "通知送達 二個營業日 補繳",
    "collateral_disposal_condition": "處分其擔保品", "remaining_debt_notice": "不足抵償債務 補足",
    "default_report": "申報違約", "forced_buy_in": "未完成反向買進 強制買回",
    "normal_settlement_obligation": "當日沖銷 相同數量 相抵", "funding_gap_estimated": "交割 違約",
}
OFFICIAL_RESOURCES = [
    {"name": "財團法人金融消費評議中心", "url": "https://www.foi.org.tw/", "note": "金融消費爭議：先向券商申訴，未獲處理可申請評議"},
    {"name": "臺灣證券交易所 法規分享知識庫", "url": "https://twse-regulation.twse.com.tw/", "note": "融資融券、當沖相關規章原文"},
    {"name": "全國法規資料庫", "url": "https://law.moj.gov.tw/", "note": "法律與命令原文"},
    {"name": "金融監督管理委員會證券期貨局", "url": "https://www.sfb.gov.tw/", "note": "證券主管機關"},
]
LIMITATIONS = [
    "本結果是模擬與教育用途，不是投資建議，也不是律師的正式法律意見。",
    "數字由程式依輸入假設計算，實際金額以券商對帳單與通知為準。",
    "僅支援單一融資部位或單筆當沖；整戶與融券部位未完整納入。",
    "規則已自動比對官方原文，但尚未全部經過具金融法律專業的人員審查。",
]


class Recorder:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.seq = 0
        self.tokens = 0

    def event(self, agent: str, status: str, message: str) -> None:
        self.seq += 1
        with service_session() as conn:
            conn.execute(text("""insert into agent_events (agent_run_id, seq, agent_name, status, message)
                                 values (:r, :s, :a, :st, :m)"""),
                         {"r": self.run_id, "s": self.seq, "a": agent, "st": status, "m": message})

    def task(self, agent: str, task_type: str, fn, depends_on: list[str] | None = None) -> Any:  # noqa: ANN001
        self.event(agent, "running", f"{agent} 開始：{task_type}")
        with service_session() as conn:
            t = one(conn, """insert into agent_tasks (agent_run_id, agent_name, task_type, status, depends_on, started_at)
                             values (:r, :a, :t, 'running', :d, now()) returning id::text""",
                    r=self.run_id, a=agent, t=task_type, d=depends_on or [])
        start = time.monotonic()
        try:
            out, meta = fn()
        except Exception as e:
            dur = int((time.monotonic() - start) * 1000)
            with service_session() as conn:
                conn.execute(text("""update agent_tasks set status='failed', error_message=:e, finished_at=now(),
                                     duration_ms=:d where id=:i"""), {"e": f"{type(e).__name__}: {e}"[:500], "d": dur,
                                                                     "i": t["id"]})
            self.event(agent, "failed", f"{agent} 失敗：{type(e).__name__}")
            raise
        dur = int((time.monotonic() - start) * 1000)
        self.tokens += int(meta.get("tokens", 0))
        with service_session() as conn:
            conn.execute(text("""update agent_tasks set status=:st, output_summary=:o, tool_calls=cast(:tc as jsonb),
                                 retrieved_sources=cast(:rs as jsonb), validation_result=cast(:v as jsonb), tokens=:tk,
                                 finished_at=now(), duration_ms=:d where id=:i"""),
                         {"st": meta.get("status", "completed"), "o": meta.get("summary", "")[:1000],
                          "tc": json.dumps(meta.get("tool_calls", []), ensure_ascii=False, default=str),
                          "rs": json.dumps(meta.get("sources", []), ensure_ascii=False, default=str),
                          "v": json.dumps(meta.get("validation"), ensure_ascii=False, default=str),
                          "tk": int(meta.get("tokens", 0)), "d": dur, "i": t["id"]})
        self.event(agent, meta.get("status", "completed"), meta.get("summary", f"{agent} 完成")[:300])
        return out


def input_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def create_run(user_id: str | None, workflow: str, payload: dict[str, Any], scenario_id: str | None = None,
               contract_id: str | None = None) -> tuple[str, bool]:
    """建立 run；相同輸入、規則版本與模型已完成過就直接重用（快取＋去重）。回傳 (run_id, cached)。"""
    info = llm.provider_info()
    # 語系不同的說明不能共用快取
    h = input_hash({"w": workflow, "p": payload, "m": info, "u": user_id, "pv": PROMPT_VERSION,
                    "loc": i18n.get_locale()})
    with service_session() as conn:
        hit = one(conn, """select id::text from agent_runs where input_hash = :h and status = 'completed'
                           and created_at > now() - interval '1 day' order by created_at desc limit 1""", h=h)
        if hit:
            return hit["id"], True
        r = one(conn, """insert into agent_runs (user_id, scenario_id, contract_id, workflow_name, input_hash, status,
                           provider, model) values (:u, :s, :c, :w, :h, 'queued', :p, :m) returning id::text""",
                u=user_id, s=scenario_id, c=contract_id, w=workflow, h=h, p=info["provider"], m=info["model"])
    return r["id"], False


def _template_explanation(result: dict[str, Any]) -> AIExplanation:
    events = [n for n in result["timeline"] if n["status"] in ("triggered_in_simulation", "requires_confirmation")]
    exps = [{"event_type": n["event_type"], "explanation": (n.get("plain_language") or n["trigger_condition"])[:600]}
            for n in events if n["event_type"] != "price_change"][:12]
    rights = sorted({r for n in events for r in n["investor_rights"]})[:8]
    obligations = sorted({r for n in events for r in n["investor_obligations"]})[:8]
    if result["trading_type"] == "margin":
        last = result["states"][-1]
        fin = (f"最後一個步驟的模擬價格是 {last['price']}，擔保維持率約 {last['maintenance_ratio_pct']}%。"
               f"融資借款 {result['opening']['financing']['value']} 元。")
    else:
        m = result["metrics"]
        fin = (f"已沖銷 {m['matched_quantity']['value']} 股，淨損益 {m['net_pnl']['value']} 元；"
               f"估計交割應付款 {m['settlement_payable']['value']} 元。")
    return AIExplanation(summary="以下說明由規則模板產生（未使用生成式 AI），內容來自已驗證的計算結果與規則。",
                         financial_summary=fin, event_explanations=exps, investor_rights=rights,
                         investor_obligations=obligations,
                         uncertainties=sorted({u for n in result["timeline"] for u in n["uncertainty"]})[:8])


def _allowed_numbers(result: dict[str, Any]) -> set[str]:
    nums: set[str] = set()

    def walk(o: Any) -> None:
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str | int | float):
            for m in __import__("re").finditer(r"\d[\d,]*(?:\.\d+)?", str(o)):
                nums.add(m.group(0).replace(",", ""))
    walk(result)
    for p in ("130", "166", "1.5", "3", "7", "10", "100", "60", "30"):
        nums.add(p)
    return nums


def run_simulation_analysis(run_id: str, trading_type: str, body: dict[str, Any],
                            contract_id: str | None = None, status_overrides: dict[str, str] | None = None,
                            locale: str = "zh-TW") -> None:
    """背景執行時 ContextVar 不一定會跟過來，所以語系由呼叫端明確傳入。"""
    token = i18n.set_locale(locale)
    try:
        _run_simulation_analysis(run_id, trading_type, body, contract_id, status_overrides)
    finally:
        i18n.reset_locale(token)


def _run_simulation_analysis(run_id: str, trading_type: str, body: dict[str, Any],
                             contract_id: str | None = None, status_overrides: dict[str, str] | None = None) -> None:
    from ..schemas.calc import DayTradeCalcIn, MarginScenarioIn
    from ..services import calc_service

    rec = Recorder(run_id)
    s = get_settings()
    with service_session() as conn:
        conn.execute(text("update agent_runs set status='running', started_at=now() where id=:i"), {"i": run_id})
    try:
        plan = ["financial_calculation", "legal_rules", "legal_retrieval"] + (["contract"] if contract_id else []) + \
               ["verification", "plain_language", "review", "report"]
        rec.task("orchestrator", "plan", lambda: (plan, {"summary": "工作流程：" + " → ".join(plan),
                                                         "validation": {"max_iterations": s.max_agent_iterations,
                                                                        "max_cost": s.max_analysis_cost}}))

        def calc():
            if trading_type == "margin":
                r = calc_service.margin_scenario(MarginScenarioIn(**body), status_overrides)
            else:
                r = calc_service.day_trade_calc(DayTradeCalcIn(**body), status_overrides)
            h = input_hash(r.get("states") or r.get("metrics"))
            return r, {"summary": f"計算完成（{r['calculation_version']}）", "tool_calls": [
                {"tool": f"financial_engine.{trading_type}", "input_hash": input_hash(body), "output_hash": h}]}
        result = rec.task("financial_calculation", "calculate", calc)
        metrics_hash = input_hash(result.get("states") or result.get("metrics"))

        def rules():
            triggered = [n["event_type"] for n in result["timeline"] if n["status"] != "not_triggered"]
            return triggered, {"summary": f"規則版本 {result['rule_version']}；事件 {len(triggered)} 個",
                               "tool_calls": [{"tool": "legal_rules.evaluate", "rule_version": result["rule_version"]}],
                               "validation": {"conflicts": result["rule_conflicts"]}}
        triggered = rec.task("legal_rules", "evaluate", rules, ["financial_calculation"])

        def retrieve():
            found: dict[str, dict] = {}
            for ev in triggered:
                q = EVENT_QUERIES.get(ev)
                if not q:
                    continue
                for it in legal_search(q, "hybrid", 3, trading_type=trading_type)["items"]:
                    a = it["article"]
                    found.setdefault(f"{a['source_key']}#{a['article_number']}", a)
            src = [{"id": k, "title": v["official_title"], "article": v["article_number"], "url": v["official_url"],
                    "version": v["version"]} for k, v in found.items()]
            return found, {"summary": f"檢索到 {len(found)} 條相關條文", "sources": src,
                           "tool_calls": [{"tool": "legal_rag.search", "queries": len(triggered)}]}
        retrieved = rec.task("legal_retrieval", "search", retrieve, ["legal_rules"])

        contract_findings: list[dict[str, Any]] = []
        if contract_id:
            def contract():
                with service_session() as conn:
                    cl = rows(conn, """select clause_number, page_number, category, original_text from contract_clauses
                                       where contract_id = :c and category in ('maintenance_ratio','margin_call','notification',
                                       'top_up_deadline','disposal','default','financing_rate','interest_method','remaining_debt')
                                       order by page_number, char_start""", c=contract_id)
                return cl, {"summary": f"取出 {len(cl)} 條相關契約條款"}
            contract_findings = rec.task("contract", "extract_relevant_clauses", contract, ["legal_rules"])

        def verify():
            citations = [b for n in result["timeline"] for b in n["legal_basis"]]
            bad = [c for c in citations if not c["validated"]]
            now_hash = input_hash(result.get("states") or result.get("metrics"))
            v = {"citations_total": len(citations), "citations_failed": len(bad),
                 "metrics_unchanged": now_hash == metrics_hash,
                 "unreviewed_rules": sorted({r["rule_id"] for r in result["rules"]
                                             if r["review_status"] not in ("active", "approved")}),
                 "rules_without_official_source": sorted({r["rule_id"] for r in result["rules"]
                                                          if not r["has_official_source"]})}
            return v, {"summary": f"引用 {len(citations)} 筆，失敗 {len(bad)} 筆；數字未被修改：{v['metrics_unchanged']}",
                       "validation": v, "status": "completed" if not bad and v["metrics_unchanged"] else "failed"}
        verification = rec.task("verification", "validate", verify, ["financial_calculation", "legal_retrieval"])

        def explain():
            if trading_type == "margin":
                last = result["states"][-1]
                key = {"融資借款": result["opening"]["financing"]["value"], "自備本金": result["opening"]["own_funds"]["value"],
                       "最後模擬價格": last["price"], "最後擔保維持率%": last["maintenance_ratio_pct"]}
            else:
                key = {k: result["metrics"][k]["value"] for k in ("matched_quantity", "unmatched_long", "unmatched_short",
                                                                  "net_pnl", "settlement_payable", "funding_gap")}
            events = [{"event_type": n["event_type"], "事件": n["title_zh"], "狀態": n["status"], "日期": n["date"],
                       "條件": n["trigger_condition"], "影響": n["financial_impact"],
                       "規則說明": (n.get("plain_language") or "")[:220]}
                      for n in result["timeline"] if n["event_type"] != "price_change"][:12]
            data = {"關鍵數字": key, "事件": events, "假設": result["assumptions"][:4]}
            if i18n.is_en():
                prompt = ("Rewrite the following verified simulation results in plain English that an ordinary "
                          "investor can understand. Use only the numbers and rule explanations below; do not add "
                          "numbers, legal articles or inferences; give no trading advice; copy each "
                          "event_explanations event_type exactly.\n"
                          + json.dumps(i18n.translate(data), ensure_ascii=False, default=str))
            else:
                prompt = ("請把下列『已驗證的模擬結果』改寫成一般投資人看得懂的繁體中文。"
                          "只能使用下面出現過的數字與規則說明，不可新增數字、法條或推論；不可給買賣建議；"
                          "event_explanations 的 event_type 必須照抄。\n"
                          + json.dumps(data, ensure_ascii=False, default=str))
            prompt = (prompt
                      + (("\n\nRelevant clauses from the user's contract (original text, for citation only):\n"
                          if i18n.is_en() else "\n\n使用者契約相關條款（原文，僅供引用）：\n")
                         + llm.untrusted("\n".join(c["original_text"] for c in contract_findings), 3000)
                         if contract_findings else ""))
            try:
                r = llm.generate(AIExplanation, prompt)
                return {"explanation": r.data, "provider": r.provider, "model": r.model}, {
                    "summary": f"{r.provider}:{r.model} 產生說明（{r.duration_ms} ms）", "tokens": r.tokens}
            except (llm.LLMUnavailable, llm.LLMOutputInvalid) as e:
                return {"explanation": _template_explanation(result), "provider": "template", "model": None,
                        "fallback_reason": str(e)}, {"summary": f"生成式 AI 不可用，改用規則模板：{e}",
                                                     "status": "completed"}
        explained = rec.task("plain_language", "explain", explain, ["verification"])

        def review():
            exp: AIExplanation = explained["explanation"]
            blob = " ".join([exp.summary, exp.financial_summary] + [e.explanation for e in exp.event_explanations]
                            + exp.investor_rights + exp.investor_obligations + exp.uncertainties)
            advice = advice_violations(blob) + misconceptions(blob)
            nums = unverified_numbers(blob, _allowed_numbers(result)) if explained["provider"] != "template" else []
            _, pii = redact_pii(blob)
            passed = not advice and not nums
            v = {"advice_violations": advice, "unverified_numbers": nums, "pii_found": pii, "passed": passed}
            if not passed:
                explained["explanation"] = _template_explanation(result)
                explained["rejected_provider"] = explained["provider"]
                explained["provider"] = "template"
            return v, {"summary": "審查通過" if passed else "AI 說明未通過審查，已改用規則模板", "validation": v}
        review_result = rec.task("review", "check", review, ["plain_language"])

        def report():
            exp: AIExplanation = explained["explanation"]
            by_event = {e.event_type: e.explanation for e in exp.event_explanations}
            out = {
                "summary": exp.summary,
                "calculation_reference": metrics_hash[:16],
                "calculation_version": result["calculation_version"],
                "rule_version": result["rule_version"],
                "legal_source_version": result.get("legal_source_version"),
                "financial_explanation": {"summary": exp.financial_summary,
                                          "verified_metrics": result.get("opening") or result.get("metrics"),
                                          "assumptions": result["assumptions"]},
                "legal_events": [{
                    "event_type": n["event_type"], "title": n["title_zh"], "status": n["status"], "date": n["date"],
                    "trigger_condition": n["trigger_condition"],
                    "explanation": (n["trigger_condition"] if n["event_type"] == "price_change"
                                    else by_event.get(n["event_type"]) or n.get("plain_language") or ""),
                    "legal_citation_ids": [f"{b['source_key']}#{b['article_number']}" for b in n["legal_basis"]],
                    "missing_facts": [u for u in n["uncertainty"] if "未知" in u or "沒有" in u]}
                    for n in result["timeline"]],
                "investor_rights": [{"description": d, "conditions": [], "citation_ids": []} for d in exp.investor_rights],
                "investor_obligations": [{"description": d, "conditions": [], "citation_ids": []}
                                         for d in exp.investor_obligations],
                "contract_findings": contract_findings,
                "retrieved_articles": [{"id": k, **{x: v[x] for x in ("official_title", "article_number", "official_url",
                                                                      "version", "content")}}
                                       for k, v in retrieved.items()],
                "uncertainties": exp.uncertainties,
                "official_resources": OFFICIAL_RESOURCES,
                "limitations": LIMITATIONS,
                "verification": verification,
                "review": review_result,
                "explanation_provider": explained["provider"],
                "explanation_model": explained.get("model"),
                "requires_professional_review": True,
                "timeline": result["timeline"],
                "simulation": result,
            }
            return out, {"summary": "已組成結構化結果"}
        final = rec.task("report", "assemble", report, ["review"])
        with service_session() as conn:
            conn.execute(text("""update agent_runs set status='completed', completed_at=now(), total_tokens=:t,
                                 output=cast(:o as jsonb) where id=:i"""),
                         {"t": rec.tokens, "o": json.dumps(final, ensure_ascii=False, default=str), "i": run_id})
        rec.event("orchestrator", "completed", "工作流程完成")
    except Exception as e:  # noqa: BLE001
        with service_session() as conn:
            conn.execute(text("""update agent_runs set status='failed', completed_at=now(), error_message=:e
                                 where id=:i"""), {"e": f"{type(e).__name__}: {e}"[:500], "i": run_id})
        rec.event("orchestrator", "failed", f"工作流程失敗：{type(e).__name__}")
        traceback.print_exc()


def today() -> date:
    return date.today()
