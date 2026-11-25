"""把一連串模擬狀態轉成法律責任時間軸。所有事件都由規則引擎判斷，這裡負責日期與狀態機。"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from ..legal_rules.engine import RuleVersion
from .events import EVENT_META


@dataclass
class TimelineNode:
    id: str
    step: int
    date: str | None
    event_type: str
    title_zh: str
    title_en: str
    status: str
    trigger_condition: str
    financial_impact: dict[str, str] = field(default_factory=dict)
    rule_ids: list[str] = field(default_factory=list)
    legal_basis: list[dict[str, Any]] = field(default_factory=list)
    contract_basis: list[str] = field(default_factory=list)
    investor_rights: list[str] = field(default_factory=list)
    investor_obligations: list[str] = field(default_factory=list)
    broker_rights: list[str] = field(default_factory=list)
    broker_obligations: list[str] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)
    deadline: str | None = None
    deadline_note: str | None = None
    uncertainty: list[str] = field(default_factory=list)
    possible_next_events: list[str] = field(default_factory=list)
    plain_language: str | None = None
    unreviewed: bool = False
    ai_checked: bool = False  # approved：原文已核對（目前由 AI 執行），尚未經律師啟用為 active
    unverified: bool = False


class TimelineBuilder:
    def __init__(self, rules: dict[str, RuleVersion]) -> None:
        self.rules = rules
        self.nodes: list[TimelineNode] = []

    def add(self, step: int, d: date | None, event_type: str, status: str, trigger: str,
            rule_ids: list[str] | None = None, impact: dict[str, Decimal | str | None] | None = None,
            deadline: date | None = None, deadline_note: str | None = None,
            uncertainty: list[str] | None = None, contract_basis: list[str] | None = None) -> TimelineNode:
        meta = EVENT_META[event_type]
        node = TimelineNode(
            id=f"{step}-{len(self.nodes)}-{event_type}", step=step, date=d.isoformat() if d else None,
            event_type=event_type, title_zh=meta["zh"], title_en=meta["en"], status=status,
            trigger_condition=trigger,
            financial_impact={k: str(v) for k, v in (impact or {}).items() if v is not None},
            deadline=deadline.isoformat() if deadline else None, deadline_note=deadline_note,
            uncertainty=list(uncertainty or []), possible_next_events=list(meta["next"]),
            contract_basis=list(contract_basis or []),
        )
        texts = []
        for rid in rule_ids or []:
            rv = self.rules.get(rid)
            if rv is None:
                node.uncertainty.append(f"規則 {rid} 目前沒有生效版本，無法提供法律依據")
                continue
            node.rule_ids.append(rid)
            node.legal_basis += [
                {**asdict(c), "rule_id": rid, "rule_version": rv.version} for c in rv.citations]
            for attr in ("investor_rights", "investor_obligations", "broker_rights", "broker_obligations",
                         "required_evidence"):
                for item in rv.raw.get(attr) or []:
                    if item not in getattr(node, attr):
                        getattr(node, attr).append(item)
            if rv.plain_language:
                texts.append(rv.plain_language)
            if rv.review_status not in ("active", "approved"):
                node.unreviewed = True
            elif rv.review_status == "approved":
                node.ai_checked = True
            if not rv.raw.get("sources"):
                node.unverified = True
                node.uncertainty.append("此事件的法律依據尚未匯入官方原文（Insufficient Legal Evidence）")
            for ex in rv.exceptions:
                node.uncertainty.append(f"例外：{ex}")
        node.plain_language = "\n".join(texts) or None
        self.nodes.append(node)
        return node

    def to_list(self) -> list[dict[str, Any]]:
        """依日期排序（沒有日期的事件放最後），同日維持加入順序。"""
        order = sorted(range(len(self.nodes)),
                       key=lambda i: (self.nodes[i].date is None, self.nodes[i].date or "", i))
        return [asdict(self.nodes[i]) for i in order]
