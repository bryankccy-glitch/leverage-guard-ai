"""從官方公開資料擷取本產品用到的法規，輸出 data/legal/documents.json。

來源：
- 全國法規資料庫開放資料（法律 ChLaw.json、命令 ChOrder.json）：https://law.moj.gov.tw/api/Ch/Law/JSON、/Order/JSON
- 臺灣證券交易所法規分享知識庫（行動版全文頁）：https://twse-regulation.twse.com.tw/m/LawContent.aspx?FID=<代碼>
- 臺灣證券交易所休市日：https://www.twse.com.tw/rwd/zh/holidaySchedule/holidaySchedule

用法：python scripts/extract_legal_sources.py <下載資料夾>
下載資料夾需含 law.zip、order.zip、twse_<代碼>.html、h_latest.json（沒有就會自動下載）。
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "legal"

MOJ_LAWS = {
    # 名稱: (來源類型, 主管機關, 適用交易類型)
    "證券交易法": ("statute", "金融監督管理委員會", ["margin", "day_trading", "general"]),
    "證券交易稅條例": ("statute", "財政部", ["day_trading", "general"]),
    "金融消費者保護法": ("statute", "金融監督管理委員會", ["general"]),
}
MOJ_ORDERS = {
    "證券商辦理有價證券買賣融資融券管理辦法": ("regulation", "金融監督管理委員會", ["margin"]),
    "證券金融事業管理規則": ("regulation", "金融監督管理委員會", ["margin"]),
    "有價證券得為融資融券標準": ("regulation", "金融監督管理委員會", ["margin"]),
}
TWSE_RULES = {
    "FL007304": ("臺灣證券交易所股份有限公司營業細則", ["day_trading", "general"]),
    "FL007121": ("證券商辦理有價證券買賣融資融券業務操作辦法", ["margin"]),
    "FL071871": ("有價證券當日沖銷交易作業辦法", ["day_trading"]),
}
UA = {"User-Agent": "Mozilla/5.0 (LeverageGuard legal ingestion)"}


def fetch(url: str, dest: Path) -> None:
    if dest.exists():
        return
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - 固定官方網址
        dest.write_bytes(r.read())


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def moj_docs(zip_path: Path, wanted: dict, retrieved_at: str) -> list[dict]:
    z = zipfile.ZipFile(zip_path)
    name = next(n for n in z.namelist() if n.endswith(".json"))
    data = json.loads(z.read(name).decode("utf-8-sig"))
    out = []
    for law in data["Laws"]:
        if law["LawName"] not in wanted or law["LawAbandonNote"]:
            continue
        source_type, authority, trading_types = wanted[law["LawName"]]
        raw_articles = law["LawArticles"]
        if isinstance(raw_articles, str):
            raise ValueError("unexpected LawArticles format")
        chapter = None
        articles = []
        for i, a in enumerate(raw_articles):
            if a["ArticleType"] == "C":
                chapter = a["ArticleContent"].strip()
                continue
            no = re.sub(r"\s+", "", a["ArticleNo"])  # 「第 2-2 條」→「第2-2條」
            articles.append({"article_number": no, "sort_order": i, "chapter": chapter,
                             "content": a["ArticleContent"].replace("\r\n", "\n").strip()})
        body = "\n".join(f"{a['article_number']} {a['content']}" for a in articles)
        pcode = re.search(r"pcode=(\w+)", law["LawURL"]).group(1)
        out.append({
            "source_key": f"moj:{pcode}", "official_title": law["LawName"], "authority": authority,
            "source_type": source_type, "publisher": "全國法規資料庫", "jurisdiction": "TW", "market": "TW",
            "trading_types": trading_types, "official_url": law["LawURL"],
            "version": law["LawModifiedDate"], "effective_note": law["LawEffectiveNote"] or None,
            "legal_status": "current", "retrieved_at": retrieved_at,
            "dataset_update": data["UpdateDate"], "content_hash": sha(body), "articles": articles,
        })
    missing = set(wanted) - {d["official_title"] for d in out}
    if missing:
        raise SystemExit(f"官方資料找不到：{missing}")
    return out


def twse_doc(code: str, title: str, trading_types: list[str], html_path: Path, retrieved_at: str) -> dict:
    raw = html_path.read_text(encoding="utf-8", errors="ignore")
    text = html.unescape(re.sub(r"<br\s*/?>", "\n", raw))
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t\r]+", " ", text)
    m = re.search(r"法規名稱：(.+?)（(\d+\.\d+\.\d+)）", text)
    if not m or m.group(1).strip() != title:
        raise SystemExit(f"{code} 標題不符：{m and m.group(1)}")
    version = m.group(2)
    body = text[m.end():]
    end = body.find("流通證券")
    body = body[:end if end > 0 else None]
    parts = re.split(r"\n\s*(?=第 \d+(?:-\d+)? 條)", body)
    articles, chapter = [], None
    for i, p in enumerate(parts):
        ch = re.findall(r"第 [一二三四五六七八九十]+ 章 [^\n]+", p)
        am = re.match(r"第 (\d+(?:-\d+)?) 條", p.strip())
        if am:
            content = p.strip()[am.end():]
            content = re.split(r"\n\s*第 [一二三四五六七八九十]+ 章 ", content)[0]
            content = "\n".join(line.strip() for line in content.strip().splitlines() if line.strip())
            # 證交所頁面是固定寬度斷行：除了款次（一、二、…）之前與句號之後，其餘換行都是排版斷行
            content = re.sub(r"\n(?![一二三四五六七八九十]+、)", "", content)
            content = re.sub(r"。(?=[^\n」）])", "。\n", content)
            articles.append({"article_number": f"第{am.group(1)}條", "sort_order": i,
                             "chapter": chapter, "content": content})
        if ch:
            chapter = ch[-1].strip()
    if len(articles) < 10:
        raise SystemExit(f"{code} 條文太少，解析可能失敗：{len(articles)}")
    joined = "\n".join(f"{a['article_number']} {a['content']}" for a in articles)
    return {
        "source_key": f"twse:{code}", "official_title": title, "authority": "臺灣證券交易所",
        "source_type": "exchange_rule", "publisher": "臺灣證券交易所法規分享知識庫", "jurisdiction": "TW",
        "market": "TWSE/TPEx", "trading_types": trading_types,
        "official_url": f"https://twse-regulation.twse.com.tw/m/LawContent.aspx?FID={code}",
        "version": version, "effective_note": None, "legal_status": "current", "retrieved_at": retrieved_at,
        "dataset_update": None, "content_hash": sha(joined), "articles": articles,
    }


def main() -> None:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / ".tmp" / "legal_raw")
    src.mkdir(parents=True, exist_ok=True)
    fetch("https://law.moj.gov.tw/api/Ch/Law/JSON", src / "law.zip")
    fetch("https://law.moj.gov.tw/api/Ch/Order/JSON", src / "order.zip")
    for code in TWSE_RULES:
        fetch(f"https://twse-regulation.twse.com.tw/m/LawContent.aspx?FID={code}", src / f"twse_{code.lower()}.html")
    fetch("https://www.twse.com.tw/rwd/zh/holidaySchedule/holidaySchedule?response=json", src / "h_latest.json")

    retrieved_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    docs = moj_docs(src / "law.zip", MOJ_LAWS, retrieved_at) + moj_docs(src / "order.zip", MOJ_ORDERS, retrieved_at)
    for code, (title, tt) in TWSE_RULES.items():
        docs.append(twse_doc(code, title, tt, src / f"twse_{code.lower()}.html", retrieved_at))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "documents.json").write_text(json.dumps({"generated_at": retrieved_at, "documents": docs},
                                                   ensure_ascii=False, indent=1), encoding="utf-8")
    hol = json.loads((src / "h_latest.json").read_text(encoding="utf-8"))
    holidays = {
        "source": "臺灣證券交易所 市場開休市日期",
        "source_url": "https://www.twse.com.tw/zh/trading/holiday.html",
        "title": hol.get("title"), "retrieved_at": retrieved_at,
        "non_trading_days": [r[0] for r in hol["data"] if "開始交易" not in r[1] and "最後交易" not in r[1]],
        "raw": hol["data"],
    }
    (OUT / "twse_holidays.json").write_text(json.dumps(holidays, ensure_ascii=False, indent=1), encoding="utf-8")
    for d in docs:
        print(d["source_key"], d["official_title"], d["version"], len(d["articles"]), "條")


if __name__ == "__main__":
    main()
