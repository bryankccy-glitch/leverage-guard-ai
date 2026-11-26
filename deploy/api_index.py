"""Vercel Python 進入點：載入 apps/api 的 FastAPI app。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.main import app  # noqa: E402,F401
