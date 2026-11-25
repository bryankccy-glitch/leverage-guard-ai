"""Regulation-as-Code 規則引擎。

- 規則是宣告式 JSON（data/rules/rules.json），條件只能用固定運算子，絕不執行任意程式碼。
- 每條規則的引用文字在載入時逐字比對官方條文；比對失敗的規則標為 citation_failed，不能執行。
- 版本選擇：依交易類型與「評估日期」挑生效中的版本；同一 rule_id 有多個生效版本時標記衝突、不自行選擇。
- 狀態優先順序：active > approved > pending_review。pending_review 只在模擬中使用，輸出會標示「尚未經人工審查」。
  draft 只有明確要求（include_drafts）時才用。
- 版本可由資料庫覆寫（後台核准後狀態變成 active），所以引擎接受外部傳入的狀態表。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
RULES_FILE = ROOT / "data" / "rules" / "rules.json"
LEGAL_FILE = ROOT / "data" / "legal" / "documents.json"

STATUS_PRIORITY = {"active": 4, "approved": 3, "pending_review": 2, "draft": 1, "superseded": 0, "suspended": 0}
OPS = {"lt", "lte", "gt", "gte", "eq", "neq", "exists", "in"}
ENGINE_VERSION = "rule-engine-1.0.0"


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text)


@lru_cache(maxsize=1)
def legal_corpus() -> dict[str, dict[str, Any]]:
    data = json.loads(LEGAL_FILE.read_text(encoding="utf-8"))
    return {d["source_key"]: d for d in data["documents"]}


@dataclass
class Citation:
    source_key: str
    official_title: str
    authority: str
    source_type: str
    article_number: str
    quote: str
    official_url: str
    version: str
    retrieved_at: str
    validated: bool
    validation_note: str | None = None


@dataclass
class RuleVersion:
    rule_id: str
    version: str
    rule_type: str
    rule_name: str
    trading_type: str
    effective_from: date | None
    effective_to: date | None
    parameters: dict[str, str]
    condition: dict | None
    event: str | None
    required_facts: list[str]
    exceptions: list[str]
    plain_language: str
    is_demo: bool
    review_status: str
    citations: list[Citation]
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    @property
    def citation_ok(self) -> bool:
        return bool(self.citations) and all(c.validated for c in self.citations)

    @property
    def sources_required(self) -> bool:
        """有來源的示範規則（虛構法規變動）預設不啟用；沒有來源的待查證規則（如 T+2）照常使用但標示。"""
        return bool(self.raw.get("sources"))

    @property
    def key(self) -> str:
        return f"{self.rule_id}@{self.version}"

    def effective_on(self, d: date) -> bool:
        return (self.effective_from is None or self.effective_from <= d) and (
            self.effective_to is None or d <= self.effective_to)


def validate_citation(src: dict[str, str]) -> Citation:
    corpus = legal_corpus()
    doc = corpus.get(src["source_key"])
    if doc is None:
        return Citation(src["source_key"], "（找不到文件）", "", "", src["article_number"], src["quote"], "", "", "",
                        False, "資料庫中沒有這份文件")
    art = next((a for a in doc["articles"] if a["article_number"] == src["article_number"]), None)
    ok = art is not None and _norm(src["quote"]) in _norm(art["content"])
    note = None if ok else ("找不到條號" if art is None else "引用文字與官方條文不符")
    return Citation(doc["source_key"], doc["official_title"], doc["authority"], doc["source_type"],
                    src["article_number"], src["quote"], doc["official_url"], doc["version"], doc["retrieved_at"],
                    ok, note)


def _date(v: str | None) -> date | None:
    return None if not v else date.fromisoformat(v)


@lru_cache(maxsize=1)
def _load_file() -> tuple[RuleVersion, ...]:
    raw = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    out = []
    for r in raw["rules"]:
        out.append(RuleVersion(
            rule_id=r["rule_id"], version=r["version"], rule_type=r["rule_type"], rule_name=r["rule_name"],
            trading_type=r["trading_type"], effective_from=_date(r.get("effective_from")),
            effective_to=_date(r.get("effective_to")), parameters=r.get("parameters") or {},
            condition=r.get("condition"), event=r.get("event"), required_facts=r.get("required_facts") or [],
            exceptions=r.get("exceptions") or [], plain_language=r.get("plain_language", ""),
            is_demo=bool(r.get("is_demo")), review_status=r.get("review_status", "pending_review"),
            citations=[validate_citation(s) for s in r.get("sources") or []], raw=r))
    return tuple(out)


def all_rule_versions(status_overrides: dict[str, str] | None = None) -> list[RuleVersion]:
    """status_overrides：{"RULE@version": "active"}，來自資料庫的人工審查結果。"""
    overrides = status_overrides or {}
    out = []
    for rv in _load_file():
        status = overrides.get(rv.key, rv.review_status)
        out.append(RuleVersion(**{**rv.__dict__, "review_status": status}))
    return out


@dataclass
class Selection:
    rules: dict[str, RuleVersion]
    conflicts: list[dict[str, Any]]
    excluded: list[dict[str, str]]


def select_rules(trading_type: str, as_of: date, *, include_drafts: bool = False, include_demo: bool = False,
                 status_overrides: dict[str, str] | None = None,
                 force_versions: dict[str, str] | None = None) -> Selection:
    """挑出 as_of 當天生效的規則版本。force_versions 用於「規則版本比較」示範。"""
    chosen: dict[str, list[RuleVersion]] = {}
    excluded = []
    for rv in all_rule_versions(status_overrides):
        if rv.trading_type not in (trading_type, "general"):
            continue
        forced = (force_versions or {}).get(rv.rule_id)
        if forced is not None:
            if rv.version == forced:
                chosen.setdefault(rv.rule_id, []).append(rv)
            continue
        if not rv.effective_on(as_of):
            excluded.append({"rule": rv.key, "reason": "不在生效期間"})
            continue
        if rv.is_demo and not include_demo and rv.sources_required:
            excluded.append({"rule": rv.key, "reason": "示範規則（未啟用示範模式）"})
            continue
        if rv.review_status == "draft" and not include_drafts:
            excluded.append({"rule": rv.key, "reason": "草稿規則"})
            continue
        if STATUS_PRIORITY.get(rv.review_status, 0) == 0:
            excluded.append({"rule": rv.key, "reason": f"狀態為 {rv.review_status}"})
            continue
        if rv.raw.get("sources") and not rv.citation_ok:
            excluded.append({"rule": rv.key, "reason": "引用驗證失敗"})
            continue
        chosen.setdefault(rv.rule_id, []).append(rv)
    rules, conflicts = {}, []
    for rid, versions in chosen.items():
        best = max(STATUS_PRIORITY.get(v.review_status, 0) for v in versions)
        top = [v for v in versions if STATUS_PRIORITY.get(v.review_status, 0) == best]
        if len(top) > 1 and len({json.dumps(v.parameters, sort_keys=True) for v in top}) > 1:
            conflicts.append({"rule_id": rid, "versions": [v.version for v in top],
                              "message": "同時有多個生效版本且參數不同，需要人工確認"})
            continue
        rules[rid] = top[0]
    return Selection(rules, conflicts, excluded)


class _Missing(Exception):
    def __init__(self, fact: str) -> None:
        self.fact = fact


def _num(v: Any) -> Any:
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, int | Decimal):
        return Decimal(v)
    if isinstance(v, str):
        try:
            return Decimal(v)
        except Exception:  # noqa: BLE001
            return v
    return v


def _eval(cond: dict, facts: dict[str, Any], params: dict[str, str]) -> bool:
    if "all" in cond:
        return all(_eval(c, facts, params) for c in cond["all"])
    if "any" in cond:
        missing = None
        for c in cond["any"]:
            try:
                if _eval(c, facts, params):
                    return True
            except _Missing as m:
                missing = m
        if missing:
            raise missing
        return False
    if "not" in cond:
        return not _eval(cond["not"], facts, params)
    op = cond.get("op")
    if op not in OPS:
        raise ValueError(f"不支援的運算子：{op}")
    name = cond["field"]
    if op == "exists":
        return facts.get(name) is not None
    if facts.get(name) is None:
        raise _Missing(name)
    left = _num(facts[name])
    if "parameter" in cond:
        right = _num(params[cond["parameter"]])
    elif "field_ref" in cond:
        if facts.get(cond["field_ref"]) is None:
            raise _Missing(cond["field_ref"])
        right = _num(facts[cond["field_ref"]])
    else:
        right = _num(cond.get("value"))
    return {
        "lt": lambda: left < right, "lte": lambda: left <= right, "gt": lambda: left > right,
        "gte": lambda: left >= right, "eq": lambda: left == right, "neq": lambda: left != right,
        "in": lambda: left in right,
    }[op]()


@dataclass
class Evaluation:
    engine_version: str
    as_of: str
    trading_type: str
    matched: list[str]
    unmatched: list[str]
    missing_facts: dict[str, list[str]]
    triggered_events: list[str]
    parameters: dict[str, dict[str, str]]
    rule_versions: dict[str, str]
    unreviewed_rules: list[str]
    unverified_rules: list[str]
    demo_rules: list[str]
    conflicts: list[dict[str, Any]]
    exceptions: dict[str, list[str]]


def evaluate(trading_type: str, facts: dict[str, Any], as_of: date, **select_kwargs: Any) -> Evaluation:
    sel = select_rules(trading_type, as_of, **select_kwargs)
    matched, unmatched, events = [], [], []
    missing: dict[str, list[str]] = {}
    for rid, rv in sel.rules.items():
        if rv.condition is None:
            continue
        try:
            ok = _eval(rv.condition, facts, rv.parameters)
        except _Missing as m:
            missing.setdefault(rid, []).append(m.fact)
            continue
        (matched if ok else unmatched).append(rid)
        if ok and rv.event:
            events.append(rv.event)
    return Evaluation(
        engine_version=ENGINE_VERSION, as_of=as_of.isoformat(), trading_type=trading_type,
        matched=matched, unmatched=unmatched, missing_facts=missing, triggered_events=events,
        parameters={rid: rv.parameters for rid, rv in sel.rules.items()},
        rule_versions={rid: rv.version for rid, rv in sel.rules.items()},
        unreviewed_rules=[rid for rid, rv in sel.rules.items() if rv.review_status not in ("active", "approved")],
        unverified_rules=[rid for rid, rv in sel.rules.items() if not rv.raw.get("sources")],
        demo_rules=[rid for rid, rv in sel.rules.items() if rv.is_demo],
        conflicts=sel.conflicts,
        exceptions={rid: rv.exceptions for rid, rv in sel.rules.items() if rv.exceptions},
    )


def param(sel_rules: dict[str, RuleVersion], rule_id: str, name: str) -> Decimal | None:
    rv = sel_rules.get(rule_id)
    if rv is None or name not in rv.parameters:
        return None
    return Decimal(rv.parameters[name])


def rule_version_label(sel_rules: dict[str, RuleVersion]) -> str:
    """整組規則的版本標籤：用於報告與歷史紀錄。"""
    import hashlib
    blob = json.dumps(sorted((k, v.version, v.review_status) for k, v in sel_rules.items()), ensure_ascii=False)
    return "rules-" + hashlib.sha256(blob.encode()).hexdigest()[:10]
