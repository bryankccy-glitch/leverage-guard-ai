"""匯入官方法規、規則版本、示範帳號與示範資料。可重複執行（冪等）。

用法：cd apps/api && .venv/bin/python -m app.services.seed
"""
from __future__ import annotations

import json
from datetime import date

from sqlalchemy import text

from ..core.db import one, service_session
from ..legal_rules.engine import LEGAL_FILE, all_rule_versions
from ..security.auth import DEMO_ACCOUNTS, ensure_profile


def _chunks(content: str, size: int = 400) -> list[str]:
    """依條文切塊；超過長度時以「項」（句號換行）為界，不在句子中間切。"""
    if len(content) <= size:
        return [content]
    parts, cur = [], ""
    for para in content.split("\n"):
        if cur and len(cur) + len(para) > size:
            parts.append(cur)
            cur = ""
        cur = f"{cur}\n{para}" if cur else para
    if cur:
        parts.append(cur)
    return parts


def seed_legal() -> dict[str, int]:
    data = json.loads(LEGAL_FILE.read_text(encoding="utf-8"))
    counts = {"documents": 0, "articles": 0, "chunks": 0}
    with service_session() as conn:
        for d in data["documents"]:
            doc = one(conn, """
                insert into legal_documents (source_key, official_title, authority, source_type, publisher,
                  jurisdiction, market, trading_types, official_url, legal_status)
                values (:k, :t, :a, :st, :p, :j, :m, :tt, :u, :ls)
                on conflict (source_key) do update set official_title = excluded.official_title,
                  official_url = excluded.official_url, trading_types = excluded.trading_types
                returning id""", k=d["source_key"], t=d["official_title"], a=d["authority"], st=d["source_type"],
                      p=d["publisher"], j=d["jurisdiction"], m=d["market"], tt=d["trading_types"],
                      u=d["official_url"], ls=d["legal_status"])
            existing = one(conn, "select id from legal_document_versions where document_id = :d and version = :v",
                           d=doc["id"], v=d["version"])
            if existing:
                continue
            conn.execute(text("update legal_document_versions set is_current = false where document_id = :d"),
                         {"d": doc["id"]})
            ver = one(conn, """
                insert into legal_document_versions (document_id, version, content_hash, source_content, retrieved_at)
                values (:d, :v, :h, cast(:c as jsonb), :r) returning id""",
                      d=doc["id"], v=d["version"], h=d["content_hash"],
                      c=json.dumps({"dataset_update": d.get("dataset_update"), "effective_note": d.get("effective_note"),
                                    "article_count": len(d["articles"])}, ensure_ascii=False),
                      r=d["retrieved_at"])
            counts["documents"] += 1
            for a in d["articles"]:
                art = one(conn, """
                    insert into legal_articles (document_version_id, article_number, sort_order, chapter, article_content)
                    values (:v, :n, :o, :c, :t) returning id""",
                          v=ver["id"], n=a["article_number"], o=a["sort_order"], c=a["chapter"], t=a["content"])
                counts["articles"] += 1
                for i, ch in enumerate(_chunks(a["content"])):
                    conn.execute(text("""insert into legal_chunks (article_id, chunk_index, chunk_text, metadata)
                                         values (:a, :i, :t, cast(:m as jsonb))"""),
                                 {"a": art["id"], "i": i, "t": ch, "m": json.dumps({
                                     "law": d["official_title"], "article": a["article_number"],
                                     "chapter": a["chapter"], "trading_types": d["trading_types"]},
                                     ensure_ascii=False)})
                    counts["chunks"] += 1
    return counts


def seed_rules() -> int:
    n = 0
    with service_session() as conn:
        for rv in all_rule_versions():
            rule = one(conn, """
                insert into legal_rules (rule_key, rule_name, rule_type, market, trading_type)
                values (:k, :n, :t, :m, :tt)
                on conflict (rule_key) do update set rule_name = case when excluded.rule_name like '【示範】%%'
                  then legal_rules.rule_name else excluded.rule_name end
                returning id""", k=rv.rule_id, n=rv.rule_name, t=rv.rule_type, m=rv.raw.get("market"),
                       tt=rv.trading_type)
            exists = one(conn, "select id from legal_rule_versions where rule_id = :r and version = :v",
                         r=rule["id"], v=rv.version)
            if exists:
                continue
            ver = one(conn, """
                insert into legal_rule_versions (rule_id, version, rule_definition, effective_from, effective_to,
                  review_status, citation_validated, is_demo)
                values (:r, :v, cast(:d as jsonb), :f, :t, 'pending_review', :c, :demo) returning id""",
                      r=rule["id"], v=rv.version, d=json.dumps(rv.raw, ensure_ascii=False), f=rv.effective_from,
                      t=rv.effective_to, c=rv.citation_ok or not rv.raw.get("sources"), demo=rv.is_demo)
            for tc in rv.raw.get("test_cases") or []:
                conn.execute(text("""insert into rule_test_cases (rule_version_id, input_parameters, expected_result)
                                     values (:v, cast(:i as jsonb), cast(:e as jsonb))"""),
                             {"v": ver["id"], "i": json.dumps(tc["facts"]), "e": json.dumps(tc["expected"])})
            n += 1
    return n


def seed_demo_regulatory_update() -> None:
    """示範法規變動（虛構）：舊規則 130% → 示範規則 140%，明確標示 is_demo。"""
    with service_session() as conn:
        if one(conn, "select id from regulatory_updates where is_demo and title like '【示範】%%'"):
            return
        doc = one(conn, "select id from legal_documents where source_key = 'twse:FL007121'")
        draft = one(conn, """select v.id from legal_rule_versions v join legal_rules r on r.id = v.rule_id
                             where r.rule_key = 'MARGIN-CALL-THRESHOLD' and v.version = '9.0.0-demo'""")
        conn.execute(text("""
            insert into regulatory_updates (document_id, title, authority, official_url, change_summary, changed_articles,
              diff, affected_trading_types, impact_analysis, draft_rule_version_id, publication_date, effective_date,
              is_demo, review_status)
            values (:d, :t, '臺灣證券交易所（虛構示範）', null, :s, cast(:ca as jsonb), cast(:diff as jsonb), '{margin}',
              cast(:imp as jsonb), :dr, :p, '2099-01-01', true, 'pending_review')"""), {
            "d": doc["id"] if doc else None,
            "t": "【示範】假設整戶擔保維持率追繳門檻由 130% 調整為 140%",
            "s": "這是虛構的法規變動，用來展示版本差異、重新計算與人工審查流程。現行規定仍為 130%。",
            "ca": json.dumps([{"article_number": "第54條"}], ensure_ascii=False),
            "diff": json.dumps([{"type": "removed", "text": "低於百分之一百三十者"},
                                {"type": "added", "text": "低於百分之一百四十者"}], ensure_ascii=False),
            "imp": json.dumps({"financial": "同一部位的追繳門檻股價上升，較早進入追繳",
                               "legal": "更早觸發補繳通知與後續處分流程"}, ensure_ascii=False),
            "dr": draft["id"] if draft else None, "p": date(2026, 11, 26)})


def seed_demo_accounts() -> None:
    for acc in DEMO_ACCOUNTS:
        ensure_profile(acc["id"], acc["email"], acc["display_name"], acc["role"])


def main() -> None:
    seed_demo_accounts()
    print("法規：", seed_legal())
    print("規則版本：", seed_rules())
    seed_demo_regulatory_update()
    from .demo_data import seed_demo_content
    print("示範內容：", seed_demo_content())


if __name__ == "__main__":
    main()
