"""Review Agent 用的確定性檢查：買賣建議、未經驗證的數字、個資。"""
from __future__ import annotations

import re
from collections.abc import Iterable

ADVICE_PATTERNS = [
    r"建議(您|你)?.{0,6}(買進|買入|賣出|賣掉|加碼|減碼|出場|進場|停損|停利)", r"(應該|可以考慮)(買|賣|加碼|減碼|出場|進場)",
    r"保證(獲利|賺)", r"穩賺", r"零風險", r"最佳(槓桿|融資比例|進場|價格)", r"(規避|逃避|躲避)(交割|清償|追繳|債務)",
    r"(會|將)(上漲|下跌)到", r"目標價", r"推薦(這|此)?(檔|支)?股票",
]
# 英文輸出（英文介面）也要擋同樣的內容，否則換語言就能繞過審查
ADVICE_PATTERNS_EN = [
    r"\b(you\s+)?(should|could\s+consider|recommend(?:ed)?(?:\s+that\s+you)?|suggest(?:ed)?(?:\s+that\s+you)?)\s+"
    r"(to\s+)?(buy|sell|add\s+to|increase|reduce|exit|enter|cut\s+losses|take\s+profits?)\b",
    r"\bguarantee[sd]?\s+(a\s+)?(profit|return|gain)s?\b", r"\brisk[- ]free\b", r"\bsure\s+(profit|win|bet)\b",
    r"\b(best|optimal)\s+(leverage|financing\s+ratio|entry|exit|price)\b",
    r"\b(avoid|evade|dodge|escape)\s+(the\s+|your\s+)?(settlement|repayment|margin\s+call|debt)s?\b",
    r"\b(will|is\s+going\s+to)\s+(rise|fall|drop|climb|go\s+up|go\s+down)\s+to\b", r"\btarget\s+price\b",
    r"\brecommend(?:ing)?\s+(this|these|the)?\s*stocks?\b",
]
ADVICE_RE = re.compile("|".join(ADVICE_PATTERNS + [f"(?i:{p})" for p in ADVICE_PATTERNS_EN]))
# 常見金融概念錯誤：出現就退回 AI 說明
MISCONCEPTION_PATTERNS = {
    r"槓桿(比例|倍數)?(為|是)?\s*1\d\d(\.\d+)?\s*%": "把擔保維持率誤稱為槓桿比例",
    r"(恢復|回到|拉回)(擔保)?維持率(至|到)\s*130": "補繳差額依第 54 條公式計算，不是補到 130%",
    r"斷頭價(為|是)": "追繳門檻股價不是確定的斷頭價",
    r"(一定|必定|必然)(會)?(被)?(斷頭|處分|違約)": "處分與違約須視通知、期限與契約而定",
    r"(?i)\bleverage\s+(ratio\s+)?(of|is)?\s*1\d\d(\.\d+)?\s*%": "把擔保維持率誤稱為槓桿比例",
    r"(?i)\b(restore|bring|return|top\s+up)\w*\s+(the\s+|your\s+)?(maintenance\s+)?ratio\s+(back\s+)?to\s+130": "補繳差額依第 54 條公式計算，不是補到 130%",
    r"(?i)\bliquidation\s+price\s+(is|of)\b": "追繳門檻股價不是確定的斷頭價",
    r"(?i)\b(definitely|certainly|inevitably|surely)\s+(be\s+)?(liquidated|disposed|default)": "處分與違約須視通知、期限與契約而定",
}
ADVICE_REQUEST_RE = re.compile(
    r"(該不該|要不要|應不應該|適不適合).{0,6}(買|賣|融資|加碼|停損|出場|進場)|哪(一)?(支|檔)股票|推薦.{0,4}股票|"
    r"最佳.{0,4}(槓桿|比例|價格)|怎麼.{0,6}(逃避|規避|不用).{0,6}(交割|還|清償|追繳)|明天.{0,4}(漲|跌)|"
    r"(?i:\b(should\s+i|is\s+it\s+(a\s+good\s+idea|wise)\s+to)\b.{0,25}\b(buy|sell|use\s+margin|add|cut\s+losses|exit|enter)\b|"
    r"\bwhich\s+stocks?\b|\brecommend\b.{0,12}\bstocks?\b|\b(best|optimal)\b.{0,12}\b(leverage|ratio|price)\b|"
    r"\bhow\s+(can|do)\s+i\b.{0,20}\b(avoid|evade|not\s+pay|skip)\b.{0,20}\b(settlement|repay\w*|margin\s+call|debt)\b|"
    r"\b(tomorrow|next\s+week)\b.{0,15}\b(rise|fall|go\s+up|go\s+down)\b)")

PII_PATTERNS = {
    "national_id": re.compile(r"\b[A-Z][12]\d{8}\b"),
    "phone": re.compile(r"\b09\d{2}[-\s]?\d{3}[-\s]?\d{3}\b"),
    "bank_account": re.compile(r"\b\d{3}-?\d{2,4}-?\d{6,8}\b"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
}

NUM_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")


def advice_violations(text: str) -> list[str]:
    return sorted({m.group(0) for m in ADVICE_RE.finditer(text)})


def misconceptions(text: str) -> list[str]:
    return [msg for pat, msg in MISCONCEPTION_PATTERNS.items() if re.search(pat, text)]


def is_advice_request(text: str) -> bool:
    return bool(ADVICE_REQUEST_RE.search(text))


def unverified_numbers(text: str, allowed: Iterable[str]) -> list[str]:
    """AI 文字中出現、但不在已驗證數字集合裡的數字（忽略 1–31 的小整數：日期、條號、天數常見）。"""
    ok = set()
    for a in allowed:
        a = str(a).replace(",", "")
        ok.add(a)
        if "." in a:
            ok.add(a.rstrip("0").rstrip("."))
    bad = []
    for m in NUM_RE.finditer(text):
        n = m.group(0).replace(",", "")
        if n in ok or (n.isdigit() and int(n) <= 31) or n.rstrip("0").rstrip(".") in ok:
            continue
        bad.append(m.group(0))
    return sorted(set(bad))


def redact_pii(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for name, rx in PII_PATTERNS.items():
        text, n = rx.subn(f"［已遮罩：{name}］", text)
        if n:
            counts[name] = n
    return text, counts
