"""繁體中文 PDF 字型：使用 PyMuPDF 內建的 Droid Sans Fallback（Apache 2.0，可散布），嵌入 PDF。

嵌入字型＋正確的 Unicode 對應，PDF 在任何電腦都能正確顯示，文字也能被複製與擷取。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .config import get_settings

FONT_NAME = "LG-CJK"


@lru_cache(maxsize=1)
def font_path() -> Path:
    import pymupdf
    p = get_settings().storage_dir.parent / "fonts" / "DroidSansFallback.ttf"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pymupdf.Font("cjk").buffer)
    return p


@lru_cache(maxsize=1)
def register_reportlab() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(font_path())))
    return FONT_NAME
