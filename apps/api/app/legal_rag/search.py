"""法律檢索：關鍵字（pg_trgm 相似度＋包含比對）、語意（pgvector，需 embedding）與混合排序（RRF）。

中文沒有空白分詞，PostgreSQL 內建全文檢索對中文效果差，所以關鍵字檢索使用 pg_trgm 三字元相似度與 ILIKE。
語意檢索需要 EMBEDDING_MODEL（例如 Ollama 的 qwen3-embedding:0.6b）且已執行 embed_chunks；
沒有 embedding 時 semantic 模式回傳空結果並說明原因，不假裝有語意檢索。
"""
from __future__ import annotations

import re
from typing import Any

import httpx

from ..core.config import get_settings
from ..core.db import rows, service_session, user_session

# 口語 → 法規用語（只用來擴充檢索詞，不影響引用內容）
QUERY_SYNONYMS = {
    "斷頭": ["處分其擔保品", "擔保維持率仍不足"], "追繳": ["補繳", "擔保維持率"], "維持率": ["擔保維持率"],
    "當沖": ["當日沖銷"], "沒賣": ["未完成", "相同數量部分相抵"], "先賣後買": ["現券賣出", "反向買進"],
    "沒買回": ["未完成反向買進", "強制買回"], "違約交割": ["違約"], "剩餘債務": ["不足抵償債務"],
    "虧完": ["不足抵償債務", "清償"], "還錢": ["清償", "補足"], "欠錢": ["不足抵償債務"],
    "交易稅": ["證券交易稅", "千分之"], "申訴": ["申訴", "評議"], "爭議": ["金融消費爭議", "評議"],
    "通知": ["通知送達"], "期限": ["營業日內"], "利息": ["融資利率"], "違約金": ["違約金"],
    "借券": ["借券", "標借"], "交割": ["交割"], "融資": ["融資"],
}


def _terms(q: str) -> list[str]:
    q = q.strip()
    terms = [t for t in re.split(r"[\s，。,、？?！!]+", q) if 2 <= len(t) <= 12]
    for k, syn in QUERY_SYNONYMS.items():
        if k in q:
            terms += syn
    return list(dict.fromkeys(terms))[:10]


def embed(text: str) -> list[float] | None:
    s = get_settings()
    if not s.embedding_model:
        return None
    try:
        r = httpx.post(f"{s.ollama_base_url}/api/embed", json={"model": s.embedding_model, "input": text}, timeout=30)
        if r.status_code != 200:
            return None
        return r.json()["embeddings"][0]
    except httpx.HTTPError:
        return None


FILTERS = """
  and (cast(:trading_type as text) is null or :trading_type = any(d.trading_types) or 'general' = any(d.trading_types))
  and (cast(:source_type as text) is null or d.source_type = :source_type)
  and (cast(:document_key as text) is null or d.source_key = :document_key)
  and v.is_current
"""

SELECT = """
  select a.id::text as article_id, a.article_number, a.chapter, a.article_content as content,
         d.source_key, d.official_title, d.authority, d.source_type, d.official_url, v.version, v.retrieved_at,
         v.content_hash
  from legal_articles a join legal_document_versions v on v.id = a.document_version_id
  join legal_documents d on d.id = v.document_id
"""


def keyword_search(conn, q: str, limit: int, **f: Any) -> list[dict[str, Any]]:
    terms = _terms(q)
    if not terms:
        return []
    likes = " or ".join(f"a.article_content ilike :t{i}" for i in range(len(terms)))
    params = {f"t{i}": f"%{t}%" for i, t in enumerate(terms)}
    hits = " + ".join(f"(case when a.article_content ilike :t{i} then {len(t)} else 0 end)" for i, t in enumerate(terms))
    hits += " + (case when a.article_number = :artno then 100 else 0 end)"
    article_match = "or a.article_number = :artno" if re.fullmatch(r"第\d+(-\d+)?條", q.replace(" ", "")) else ""
    sql = f"""{SELECT.replace('select a.id', f'select ({hits}) + similarity(a.article_content, :q) as score, a.id')}
      where (({likes}) or similarity(a.article_content, :q) > 0.05 {article_match}) {FILTERS}
      order by score desc, d.source_key, a.sort_order limit :limit"""
    return rows(conn, sql, q=q, limit=limit, artno=q.replace(" ", ""), **params, **f)


def semantic_search(conn, q: str, limit: int, **f: Any) -> list[dict[str, Any]] | None:
    vec = embed(q)
    if vec is None:
        return None
    sql = f"""{SELECT.replace('select a.id', 'select 1 - (c.embedding <=> cast(:vec as vector)) as score, a.id')}
      join legal_chunks c on c.article_id = a.id
      where c.embedding is not null {FILTERS}
      order by c.embedding <=> cast(:vec as vector) limit :limit"""
    return rows(conn, sql, vec=str(vec), limit=limit, **f)


def search(q: str, mode: str = "hybrid", limit: int = 10, trading_type: str | None = None,
           source_type: str | None = None, document_key: str | None = None) -> dict[str, Any]:
    f = {"trading_type": trading_type, "source_type": source_type, "document_key": document_key}
    notes = []
    if re.fullmatch(r"第\d+(-\d+)?條", q.replace(" ", "")):
        mode = "keyword"  # 條號查詢不需要語意檢索
    with user_session(None) as conn:
        kw = keyword_search(conn, q, limit * 2, **f) if mode in ("keyword", "hybrid") else []
        sem = semantic_search(conn, q, limit * 2, **f) if mode in ("semantic", "hybrid") else []
    if sem is None:
        sem = []
        notes.append("語意檢索未啟用：尚未設定 EMBEDDING_MODEL 或尚未建立向量，結果只來自關鍵字檢索")
    scores: dict[str, float] = {}
    by_id: dict[str, dict[str, Any]] = {}
    # RRF：語意檢索權重較高（口語問題較準）；關鍵字命中可補強條號與專有名詞
    expanded = any(k in q for k in QUERY_SYNONYMS)  # 口語詞已對應到法規用語時，關鍵字結果較可靠
    for ranked, weight in ((kw, 1.3 if expanded else 0.8), (sem, 1.0)):
        for rank, r in enumerate(ranked):
            scores[r["article_id"]] = scores.get(r["article_id"], 0) + weight / (20 + rank)
            by_id.setdefault(r["article_id"], r)
    ordered = sorted(scores, key=lambda k: -scores[k])[:limit]
    items = []
    for aid in ordered:
        r = dict(by_id[aid])
        r.pop("score", None)
        r["retrieved_at"] = str(r["retrieved_at"])
        terms = _terms(q)
        r["highlights"] = [t for t in terms if t in r["content"]]
        items.append({"article": r, "score": round(scores[aid], 5)})
    return {"items": items, "mode": mode, "notes": notes}


def embed_all_chunks(batch: int = 32) -> int:
    """替尚未有向量的法規段落建立 embedding（系統工作）。"""
    s = get_settings()
    if not s.embedding_model:
        return 0
    n = 0
    with service_session() as conn:
        todo = rows(conn, "select id::text, chunk_text from legal_chunks where embedding is null limit 5000")
    for i in range(0, len(todo), batch):
        part = todo[i:i + batch]
        try:
            r = httpx.post(f"{s.ollama_base_url}/api/embed", timeout=120,
                           json={"model": s.embedding_model, "input": [p["chunk_text"] for p in part]})
            vecs = r.json()["embeddings"]
        except Exception:  # noqa: BLE001
            break
        with service_session() as conn:
            from sqlalchemy import text
            for p, v in zip(part, vecs, strict=True):
                conn.execute(text("update legal_chunks set embedding = cast(:v as vector), embedding_model = :m where id = :i"),
                             {"v": str(v), "m": s.embedding_model, "i": p["id"]})
        n += len(part)
    return n
