"""Context-aware Legal Copilot。

流程：
1. 先用確定性規則判斷是否在要求投資建議 → 是的話拒答，改說明可試算的客觀風險與規定。
2. Scenario Agent：解析「再跌 10%」「跌到 70 元」這類假設（正規表示式，不靠 LLM），呼叫情境引擎重算並比較前後。
3. 其他問題：法規檢索 → 千問依檢索到的條文回答；回答引用的條文 ID 必須在檢索結果中，否則移除並標示。
4. 模型不可用時，直接回傳檢索到的條文與規則白話說明。
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from ..legal_rag.search import search as legal_search
from ..legal_rules.engine import all_rule_versions
from . import llm
from .guards import advice_violations, is_advice_request
from .schemas import CopilotAnswer

REFUSAL = ("我不能提供個股買賣、進出場時機、槓桿比例或股價預測的建議，也不能協助規避交割或清償義務。"
           "我可以幫你：用目前的模擬參數試算不同價格下的維持率與損益、說明追繳與擔保品處分的規定、"
           "或整理你契約中的通知與處分條款。")

DROP_RE = re.compile(r"(?:再)?(?:下跌|跌)\s*(\d+(?:\.\d+)?)\s*%")
RISE_RE = re.compile(r"(?:再)?(?:上漲|漲)\s*(\d+(?:\.\d+)?)\s*%")
PRICE_RE = re.compile(r"(?:跌到|漲到|變成|到)\s*(\d+(?:\.\d+)?)\s*元")


def parse_scenario(message: str, current_price: Decimal) -> dict[str, Any] | None:
    """Scenario Agent（確定性）：回傳新的模擬價格與計算基準說明。"""
    if m := DROP_RE.search(message):
        pct = Decimal(m.group(1))
        if not (0 < pct < 100):
            return None
        return {"new_price": (current_price * (1 - pct / 100)).quantize(Decimal("0.01")),
                "basis": f"以目前模擬價格 {current_price} 元為基準下跌 {pct}%"}
    if m := RISE_RE.search(message):
        pct = Decimal(m.group(1))
        return {"new_price": (current_price * (1 + pct / 100)).quantize(Decimal("0.01")),
                "basis": f"以目前模擬價格 {current_price} 元為基準上漲 {pct}%"}
    if m := PRICE_RE.search(message):
        p = Decimal(m.group(1))
        if p <= 0:
            return None
        return {"new_price": p, "basis": f"直接把模擬價格設為 {p} 元"}
    return None


def answer(message: str, context: dict[str, Any] | None) -> dict[str, Any]:
    from ..schemas.calc import MarginCalcIn
    from ..services import calc_service

    message = message.strip()[:1000]
    tools: list[dict[str, Any]] = []
    if is_advice_request(message):
        return {"answer": REFUSAL, "kind": "refusal", "citations": [], "tool_calls": [], "comparison": None,
                "provider": "rule"}

    comparison = None
    ctx = context or {}
    if ctx.get("trading_type") == "margin" and ctx.get("input"):
        inp = dict(ctx["input"])
        cur = Decimal(str(inp.get("current_price") or inp.get("buy_price")))
        sc = parse_scenario(message, cur)
        if sc:
            before = calc_service.margin_calc(MarginCalcIn(**{**inp, "curve": False}))
            after = calc_service.margin_calc(MarginCalcIn(**{**inp, "current_price": str(sc["new_price"]),
                                                             "curve": False}))
            keys = ["market_value", "gross_pnl", "net_pnl", "maintenance_ratio", "margin_call_amount", "equity"]
            comparison = {"basis": sc["basis"], "new_price": str(sc["new_price"]),
                          "before": {k: before["metrics"][k]["value"] for k in keys},
                          "after": {k: after["metrics"][k]["value"] for k in keys},
                          "labels": {k: after["metrics"][k]["label"] for k in keys},
                          "events_before": before["rule_evaluation"]["triggered_events"],
                          "events_after": after["rule_evaluation"]["triggered_events"]}
            tools.append({"tool": "financial_engine.margin", "price": str(sc["new_price"])})
            tools.append({"tool": "legal_rules.evaluate", "rule_version": after["rule_version"]})
            message = message + "（情境試算已完成，請說明前後差異代表的法律意義）"

    trading_type = ctx.get("trading_type") if ctx.get("trading_type") in ("margin", "day_trading") else None
    found = legal_search(message, "hybrid", 6, trading_type=trading_type)["items"]
    tools.append({"tool": "legal_rag.search", "results": len(found)})
    articles = {f"{i['article']['source_key']}#{i['article']['article_number']}": i["article"] for i in found}
    rules = [rv for rv in all_rule_versions() if rv.trading_type in (trading_type or "margin", "general")][:12]

    prompt = ("使用者問題：" + llm.untrusted(message, 1000) + "\n\n"
              + ("情境試算結果（已由計算引擎驗證，不可修改數字）：" + str(comparison) + "\n\n" if comparison else "")
              + "可引用的條文（只能引用這些 ID）：\n"
              + "\n".join(f"[{k}] {v['official_title']} {v['article_number']}：{v['content'][:500]}"
                          for k, v in articles.items())
              + "\n\n規則白話摘要：\n" + "\n".join(f"- {r.rule_name}：{r.plain_language}" for r in rules)
              + "\n\n請用繁體中文回答，說明條件與不確定性；cited_article_ids 只能填上面方括號內的 ID。")
    try:
        r = llm.generate(CopilotAnswer, prompt)
        ans: CopilotAnswer = r.data
        cited = [c for c in ans.cited_article_ids if c in articles]
        dropped = [c for c in ans.cited_article_ids if c not in articles]
        violations = advice_violations(ans.answer)
        if violations:
            return {"answer": REFUSAL, "kind": "refusal", "citations": [], "tool_calls": tools,
                    "comparison": comparison, "provider": r.provider,
                    "review": {"advice_violations": violations}}
        return {"answer": ans.answer, "kind": "answer", "uncertainties": ans.uncertainties,
                "citations": [{"id": c, **{k: articles[c][k] for k in ("official_title", "article_number", "official_url",
                                                                       "version", "content")}} for c in cited],
                "dropped_citations": dropped, "tool_calls": tools, "comparison": comparison,
                "provider": r.provider, "model": r.model}
    except (llm.LLMUnavailable, llm.LLMOutputInvalid) as e:
        text_lines = ["生成式 AI 目前無法使用，以下是系統依你的問題檢索到的官方條文與規則說明：", ""]
        text_lines += [f"・{r.rule_name}：{r.plain_language}" for r in rules[:4]]
        return {"answer": "\n".join(text_lines), "kind": "retrieval_only", "fallback_reason": str(e),
                "citations": [{"id": k, **{x: v[x] for x in ("official_title", "article_number", "official_url",
                                                             "version", "content")}} for k, v in list(articles.items())[:4]],
                "tool_calls": tools, "comparison": comparison, "provider": "none"}
