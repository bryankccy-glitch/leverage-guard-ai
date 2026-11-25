"""Request ID、簡易限流、安全標頭。"""
from __future__ import annotations

import re
import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import get_settings

_hits: dict[str, deque[float]] = defaultdict(deque)
_RID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        rid = request.headers.get("x-request-id", "")
        request.state.request_id = rid if _RID.match(rid) else uuid.uuid4().hex
        # 限流：依 IP＋授權標頭前綴（不記錄完整 token）
        limit = get_settings().rate_limit_per_minute
        key = f"{request.client.host if request.client else 'x'}:{request.headers.get('authorization', '')[-16:]}"
        now = time.monotonic()
        q = _hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= limit and not request.url.path.endswith(("/health", "/ready")):
            return JSONResponse({"error": {"code": "rate_limited", "message": "請求太頻繁，請稍後再試",
                                           "request_id": request.state.request_id, "details": None}},
                                status_code=429, headers={"Retry-After": "30"})
        q.append(now)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        path = request.url.path
        if path.startswith("/api/v1/contracts/") and path.endswith("/file"):
            # 契約原文只允許被本站前端嵌入檢視（簽名連結＋限定來源）
            origins = " ".join(get_settings().origins)
            response.headers["Content-Security-Policy"] = f"default-src 'none'; frame-ancestors {origins}"
        else:
            response.headers["X-Frame-Options"] = "DENY"
            if not path.startswith("/api/v1/docs"):
                response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response
