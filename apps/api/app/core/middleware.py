"""Request ID、簡易限流、安全標頭。"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import re
import time
import uuid
from collections import defaultdict, deque
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from .. import i18n
from .config import get_settings

_hits: dict[str, deque[float]] = defaultdict(deque)
_RID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_log = logging.getLogger(__name__)


def client_ip(request: Request) -> str:
    """真實來源 IP。serverless（Vercel）在代理後面，request.client 是平台位址，改讀 x-forwarded-for 第一段。"""
    if get_settings().serverless:
        fwd = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if fwd:
            return fwd
        real = request.headers.get("x-real-ip", "").strip()
        if real:
            return real
    return request.client.host if request.client else "x"


def rate_key(request: Request) -> str:
    """IP＋授權標頭的雜湊：同一 IP 的不同帳號分開計數，且不保存任何 token 內容。"""
    auth = request.headers.get("authorization", "")
    digest = hashlib.sha256(auth.encode()).hexdigest()[:16] if auth else "-"
    return f"{client_ip(request)}:{digest}"


def _memory_hits(key: str) -> int:
    """單一實例的滑動視窗計數（本機與資料庫故障時的退路）。回傳加入本次後的次數。"""
    now = time.monotonic()
    q = _hits[key]
    while q and now - q[0] > 60:
        q.popleft()
    q.append(now)
    return len(q)


def _db_hits(key: str) -> int:
    """跨實例共用的分鐘視窗計數（原子 upsert）。偶爾順便清掉 10 分鐘前的舊視窗。"""
    from sqlalchemy import text

    from .db import engine

    window = datetime.now(UTC).replace(second=0, microsecond=0)
    with engine().begin() as conn:
        hits = conn.execute(text(
            "insert into public.api_rate_limits (bucket, window_start, hits) values (:b, :w, 1) "
            "on conflict (bucket, window_start) do update set hits = api_rate_limits.hits + 1 returning hits"),
            {"b": key, "w": window}).scalar_one()
        if random.random() < 0.01:
            conn.execute(text("delete from public.api_rate_limits where window_start < now() - interval '10 minutes'"))
    return int(hits)


async def count_hit(key: str) -> int:
    if get_settings().serverless:
        try:
            return await run_in_threadpool(_db_hits, key)
        except Exception:  # noqa: BLE001 - 限流壞掉不能讓整個 API 停擺
            _log.warning("資料庫限流失敗，改用單機計數", exc_info=True)
    return _memory_hits(key)


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        token = i18n.set_locale(i18n.parse_accept_language(request.headers.get("accept-language")))
        try:
            response = await _handle(request, call_next)
        finally:
            i18n.reset_locale(token)
        return response

    async def _handle(request: Request, call_next):  # type: ignore[no-untyped-def]
        rid = request.headers.get("x-request-id", "")
        request.state.request_id = rid if _RID.match(rid) else uuid.uuid4().hex
        # 限流：依真實 IP＋授權標頭雜湊；serverless 用資料庫跨實例共用計數
        if not request.url.path.endswith(("/health", "/ready")):
            hits = await count_hit(rate_key(request))
            if hits > get_settings().rate_limit_per_minute:
                return JSONResponse({"error": {"code": "rate_limited", "message": i18n.tr("請求太頻繁，請稍後再試"),
                                               "request_id": request.state.request_id, "details": None}},
                                    status_code=429, headers={"Retry-After": "30"})
        response = await call_next(request)
        if i18n.is_en() and response.headers.get("content-type", "").startswith("application/json"):
            response = await _translate_json(response)
        response.headers["Vary"] = "Accept-Language"
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


async def _translate_json(response):  # type: ignore[no-untyped-def]
    """英文模式：把 JSON 回應中已知的中文字串換成英文（見 app/i18n.py）。"""
    body = b"".join([chunk async for chunk in response.body_iterator])
    try:
        data = json.loads(body)
    except ValueError:
        return Response(body, status_code=response.status_code, headers=_strip_length(response.headers))
    out = json.dumps(i18n.translate(data), ensure_ascii=False).encode()
    return Response(out, status_code=response.status_code, headers=_strip_length(response.headers),
                    media_type="application/json")


def _strip_length(headers):  # type: ignore[no-untyped-def]
    return {k: v for k, v in headers.items() if k.lower() != "content-length"}
