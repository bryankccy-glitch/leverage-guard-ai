"""LeverageGuard AI API。啟動：cd apps/api && .venv/bin/uvicorn app.main:app --reload --port 8000"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .api import admin, public, user
from .core import errors, middleware
from .core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

settings = get_settings()
app = FastAPI(title="LeverageGuard AI API", version="0.1.0",
              description="金融交易風險與法律責任情境模擬平台。所有計算結果皆為模擬，不構成投資建議或法律意見。",
              openapi_url="/api/v1/openapi.json", docs_url="/api/v1/docs", redoc_url=None)
middleware.install(app)
# CORS 最後加入＝最外層：限流回應（429）與錯誤回應也會帶 CORS 標頭，前端才能讀到錯誤內容
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=False,
                   allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
                   allow_headers=["Authorization", "Content-Type", "X-Request-ID"], expose_headers=["X-Request-ID"])
errors.install(app)
for r in (public.router, user.router, admin.router):
    app.include_router(r, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """直接打開 API 網址時，導向前端網站（API 文件在 /api/v1/docs）。"""
    return RedirectResponse(settings.web_url, status_code=307)
