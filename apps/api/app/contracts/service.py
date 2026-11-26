"""契約智慧分析。

- 檔案驗證：只收 PDF、PNG、JPEG、純文字；檢查實際檔頭（magic bytes），不信任副檔名；大小上限 MAX_UPLOAD_SIZE。
- 儲存：apps/api/var/storage/<user>/<sha256>，原檔不覆寫；下載走有時效的簽名 URL。
- 擷取：PyMuPDF 逐頁取文字；圖片目前沒有 OCR（需要視覺模型），會標示「需要文字層」。
- 條款：先用確定性規則切「第 N 條」並依關鍵字分類，再請千問寫白話說明；AI 引用的原文必須真的出現在文件中，否則丟棄。
- 文件內容視為不可信資料，不執行其中任何指令；私人契約內容不寫入一般 log。
"""
from __future__ import annotations

import hashlib
import hmac
import re
import time
from pathlib import Path
from typing import Any

from ..agents import llm
from ..agents.guards import redact_pii
from ..agents.schemas import ContractAIResult
from ..core.config import get_settings

MAGIC = {b"%PDF-": "application/pdf", b"\x89PNG\r\n\x1a\n": "image/png", b"\xff\xd8\xff": "image/jpeg"}

# 類別關鍵字：先比對條款標題（第一行），標題沒有命中才看內文命中次數
CATEGORY_KEYWORDS = [
    ("top_up_deadline", ["補繳期限", "營業日內"]), ("financing_rate", ["利率", "年息"]), ("interest_method", ["計息", "利息"]),
    ("maintenance_ratio", ["維持率"]), ("margin_call", ["追繳", "補繳"]), ("financing_term", ["期限", "期間", "展延"]),
    ("disposal", ["處分"]), ("default", ["違約"]), ("fees", ["手續費", "費用"]), ("collateral", ["擔保品", "抵繳"]),
    ("notification", ["通知", "送達"]), ("remaining_debt", ["不足", "清償"]), ("termination", ["終止", "解除"]),
    ("dispute", ["爭議", "評議", "管轄"]), ("personal_data", ["個人資料", "個資"]),
]
PARAM_PATTERNS = {
    "maintenance_ratio_pct": re.compile(r"維持率[^。\n]{0,20}?(?:低於|未達)\s*(?:百分之)?([0-9一二三四五六七八九十百]+)\s*%?"),
    "annual_rate_pct": re.compile(r"(?:年利率|年息|利率)[^。]{0,12}?([0-9]+(?:\.[0-9]+)?)\s*%"),
    "top_up_business_days": re.compile(r"([0-9一二三四五]+)\s*個?營業日內"),
}


def sniff(data: bytes, filename: str) -> str | None:
    for sig, mime in MAGIC.items():
        if data.startswith(sig):
            return mime
    if filename.lower().endswith(".txt"):
        try:
            data.decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            return None
    return None


def store(user_id: str, data: bytes) -> tuple[str, str]:
    h = hashlib.sha256(data).hexdigest()
    if get_settings().storage_backend == "db":
        from sqlalchemy import text as sql

        from ..core.db import service_session
        rel = f"{user_id}/{h}"
        with service_session() as conn:
            conn.execute(sql("insert into stored_files (path, data) values (:p, :d) on conflict (path) do nothing"),
                         {"p": rel, "d": data})
        return rel, h
    d = get_settings().storage_dir / user_id
    d.mkdir(parents=True, exist_ok=True)
    p = d / h
    if not p.exists():
        p.write_bytes(data)
    return str(p.relative_to(get_settings().storage_dir)), h


def read_file(rel: str) -> bytes:
    if get_settings().storage_backend == "db":
        from ..core.db import one, service_session
        with service_session() as conn:
            r = one(conn, "select data from stored_files where path = :p", p=rel)
        if r is None:
            raise FileNotFoundError(rel)
        return bytes(r["data"])
    return storage_path(rel).read_bytes()


def delete_file(rel: str) -> None:
    if get_settings().storage_backend == "db":
        from sqlalchemy import text as sql

        from ..core.db import service_session
        with service_session() as conn:
            conn.execute(sql("delete from stored_files where path = :p"), {"p": rel})
        return
    storage_path(rel).unlink(missing_ok=True)


def storage_path(rel: str) -> Path:
    base = get_settings().storage_dir.resolve()
    p = (base / rel).resolve()
    if base not in p.parents:
        raise ValueError("非法路徑")
    return p


def sign(resource_id: str, ttl: int = 300) -> str:
    exp = int(time.time()) + ttl
    mac = hmac.new(get_settings().jwt_secret.encode(), f"{resource_id}:{exp}".encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{mac}"


def verify_sig(resource_id: str, token: str) -> bool:
    try:
        exp_s, mac = token.split(".", 1)
        exp = int(exp_s)
    except ValueError:
        return False
    good = hmac.new(get_settings().jwt_secret.encode(), f"{resource_id}:{exp}".encode(), hashlib.sha256).hexdigest()
    return exp >= time.time() and hmac.compare_digest(good, mac)


def extract_pages(data: bytes, mime: str) -> tuple[list[str], list[str]]:
    notes: list[str] = []
    if mime == "application/pdf":
        import pymupdf
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            if doc.page_count > 60:
                notes.append("文件超過 60 頁，只分析前 60 頁")
            pages = [doc[i].get_text("text") for i in range(min(doc.page_count, 60))]
        if not any(p.strip() for p in pages):
            notes.append("PDF 沒有文字層（可能是掃描檔），目前未啟用 OCR，無法擷取條款")
        return pages, notes
    if mime == "text/plain":
        return [data.decode("utf-8")], notes
    notes.append("圖片需要 OCR／視覺模型才能擷取文字，目前未啟用；請改上傳有文字層的 PDF 或貼上文字")
    return [], notes


def split_clauses(pages: list[str]) -> list[dict[str, Any]]:
    clauses = []
    for pno, page in enumerate(pages, start=1):
        parts = re.split(r"(?=第\s*[一二三四五六七八九十百0-9]+\s*條)", page)
        offset = 0
        for part in parts:
            body = part.strip()
            start = page.find(part, offset)
            offset = max(offset, start + len(part))
            if len(body) < 8:
                continue
            m = re.match(r"第\s*([一二三四五六七八九十百0-9]+)\s*條", body)
            if not m and clauses and pno > 1 and start <= 5:
                # 跨頁：頁首沒有條號的段落接回上一條
                clauses[-1]["original_text"] = (clauses[-1]["original_text"] + "\n" + body)[:2000]
                continue
            clauses.append({"clause_number": f"第{m.group(1)}條" if m else None, "page_number": pno,
                            "char_start": start, "char_end": start + len(part), "original_text": body[:2000]})
    return clauses


def categorize(text: str) -> str:
    title = text.strip().split("\n", 1)[0]
    for cat, kws in CATEGORY_KEYWORDS:
        if any(k in title for k in kws):
            return cat
    best, score = "other", 0
    for cat, kws in CATEGORY_KEYWORDS:
        n = sum(text.count(k) for k in kws)
        if n > score:
            best, score = cat, n
    return best


def extract_params(text: str) -> dict[str, str]:
    out = {}
    for k, rx in PARAM_PATTERNS.items():
        if m := rx.search(text):
            out[k] = m.group(1)
    return out


EXPECTED = ["financing_rate", "interest_method", "maintenance_ratio", "margin_call", "notification",
            "top_up_deadline", "disposal", "default", "fees", "dispute"]


def deterministic(pages: list[str]) -> dict[str, Any]:
    """確定性部分：遮罩個資、切條款、分類、擷取參數、列出文件中找不到的類別。"""
    _, pii = redact_pii("\n".join(pages))
    clauses = split_clauses([redact_pii(p)[0] for p in pages])
    for c in clauses:
        c["category"] = categorize(c["original_text"])
        c["extracted_parameters"] = extract_params(c["original_text"])
    found = {c["category"] for c in clauses}
    # 「通知方式」也可能寫在維持率條款內：只要全文提到通知方式就不列為缺漏
    full = "\n".join(pages)
    if "通知" in full:
        found.add("notification")
    return {"clauses": clauses, "pii_redacted": pii, "not_found_categories": [c for c in EXPECTED if c not in found]}


def ai_notes(pages: list[str]) -> dict[str, Any]:
    """LLM 白話說明；AI 引用的原文必須能在文件中找到，否則捨棄。"""
    redacted, _ = redact_pii("\n".join(pages))
    norm_doc = re.sub(r"\s+", "", redacted)
    try:
        r = llm.generate(ContractAIResult, "請分析下列證券商契約，逐條說明投資人的權利與義務。quote 必須逐字摘自文件原文。"
                                           "不得因條款不利就判定違法或無效；文件沒有的內容不要補。\n"
                                           + llm.untrusted(redacted, 10000))
    except (llm.LLMUnavailable, llm.LLMOutputInvalid) as e:
        return {"ai_clauses": [], "provider": "none", "model": None, "document_type": "unknown", "pending_questions": [],
                "note": f"生成式 AI 不可用，只提供確定性條款切分與分類：{e}"}
    items = []
    for it in r.data.clauses:
        q = re.sub(r"\s+", "", it.quote)
        if len(q) >= 6 and q in norm_doc:
            items.append({**it.model_dump(), "verified_in_document": True})
    dropped = len(r.data.clauses) - len(items)
    return {"ai_clauses": items, "provider": r.provider, "model": r.model, "document_type": r.data.document_type,
            "pending_questions": r.data.pending_questions,
            "note": f"AI 有 {dropped} 筆引用在文件中找不到，已捨棄" if dropped else None}


def analyze(pages: list[str]) -> dict[str, Any]:
    base = deterministic(pages)
    return {**base, **ai_notes(pages)}


def compare(analyses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """契約比較：每個類別列出各份契約的原文；缺的就寫「文件中未找到相關條款」，不自行補。"""
    cats = [c for c, _ in CATEGORY_KEYWORDS]
    out = []
    for cat in cats:
        row = {"category": cat, "contracts": []}
        for a in analyses:
            hits = [c for c in a["clauses"] if c["category"] == cat]
            row["contracts"].append({
                "contract_id": a["contract_id"], "document_name": a["document_name"],
                "found": bool(hits),
                "clauses": [{k: h[k] for k in ("clause_number", "page_number", "original_text", "extracted_parameters")}
                            for h in hits][:3] or None,
                "message": None if hits else "文件中未找到相關條款"})
        out.append(row)
    return out
