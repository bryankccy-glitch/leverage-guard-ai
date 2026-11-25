"""法規變動監察（Regulatory Watch Agent）。

Fetch → Validate → Detect Changes → Compare Versions → Classify Impact → 建立待審查更新 → 人工審查 → 通知。
- 來源：scripts/extract_legal_sources.py 產生的官方資料（LEGAL_SOURCE_SYNC_ENABLED=true 時才會重新下載）。
- 只建立 pending_review 的更新紀錄；AI 不會直接發布規則到計算引擎。
"""
from __future__ import annotations

import difflib
import json
from typing import Any

from sqlalchemy import text

from ..core.db import one, rows, service_session
from ..legal_rules.engine import LEGAL_FILE, all_rule_versions

IMPACT_KEYWORDS = {"margin": ["維持率", "追繳", "補繳", "處分", "融資"], "day_trading": ["當日沖銷", "當沖", "強制買回"],
                   "general": ["交易稅", "爭議", "申訴"]}


def article_diff(old: dict[str, str], new: dict[str, str]) -> list[dict[str, Any]]:
    changes = []
    for no in sorted(set(old) | set(new), key=lambda x: (len(x), x)):
        a, b = old.get(no), new.get(no)
        if a == b:
            continue
        kind = "added" if a is None else "removed" if b is None else "modified"
        ops = []
        if kind == "modified":
            sm = difflib.SequenceMatcher(a=a, b=b)
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag != "equal":
                    ops.append({"op": tag, "removed": a[i1:i2], "added": b[j1:j2]})
        changes.append({"article_number": no, "change": kind, "ops": ops[:20]})
    return changes


def classify(changes: list[dict[str, Any]], new_articles: dict[str, str]) -> list[str]:
    types = set()
    for c in changes:
        txt = new_articles.get(c["article_number"], "") + " ".join(o["added"] + o["removed"] for o in c["ops"])
        for t, kws in IMPACT_KEYWORDS.items():
            if any(k in txt for k in kws):
                types.add(t)
    return sorted(types)


def affected_rules(source_key: str, changed: list[str]) -> list[str]:
    out = []
    for rv in all_rule_versions():
        for s in rv.raw.get("sources") or []:
            if s["source_key"] == source_key and s["article_number"] in changed:
                out.append(rv.key)
    return sorted(set(out))


def check_for_updates() -> dict[str, Any]:
    """比較 data/legal/documents.json（最新抓取）與資料庫目前版本；有差異就建立待審查的更新紀錄。"""
    data = json.loads(LEGAL_FILE.read_text(encoding="utf-8"))
    created, unchanged = [], 0
    with service_session() as conn:
        for d in data["documents"]:
            cur = one(conn, """select v.id::text, v.version, v.content_hash, ld.id::text as doc_id from legal_document_versions v
                               join legal_documents ld on ld.id = v.document_id
                               where ld.source_key = :k and v.is_current""", k=d["source_key"])
            if cur is None or cur["content_hash"] == d["content_hash"]:
                unchanged += 1
                continue
            old = {r["article_number"]: r["article_content"] for r in rows(
                conn, "select article_number, article_content from legal_articles where document_version_id = :v", v=cur["id"])}
            new = {a["article_number"]: a["content"] for a in d["articles"]}
            changes = article_diff(old, new)
            changed_nos = [c["article_number"] for c in changes]
            conn.execute(text("""insert into regulatory_updates (document_id, title, authority, official_url, change_summary,
                                 changed_articles, diff, affected_trading_types, impact_analysis, is_demo, review_status)
                                 values (:d, :t, :a, :u, :s, cast(:ca as jsonb), cast(:df as jsonb), :tt, cast(:im as jsonb),
                                 false, 'pending_review')"""), {
                "d": cur["doc_id"], "t": f"{d['official_title']} 版本 {cur['version']} → {d['version']}",
                "a": d["authority"], "u": d["official_url"], "s": f"偵測到 {len(changes)} 條條文變動，待人工審查",
                "ca": json.dumps([{"article_number": n} for n in changed_nos], ensure_ascii=False),
                "df": json.dumps(changes, ensure_ascii=False), "tt": classify(changes, new),
                "im": json.dumps({"affected_rules": affected_rules(d["source_key"], changed_nos),
                                  "note": "受影響的規則需由法律審查員確認後建立新版本，不會自動套用"},
                                 ensure_ascii=False)})
            created.append(d["source_key"])
    return {"created": created, "unchanged": unchanged}
