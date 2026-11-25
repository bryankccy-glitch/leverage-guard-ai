"""統一錯誤格式：{"error": {"code", "message", "request_id", "details"}}。不把內部例外內容回給前端。"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..financial_engine.validation import CalculationInputError

log = logging.getLogger("leverage.errors")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: Any = None) -> None:
        self.status, self.code, self.message, self.details = status, code, message, details


def _body(request: Request, code: str, message: str, details: Any = None) -> dict:
    return {"error": {"code": code, "message": message, "request_id": getattr(request.state, "request_id", None),
                      "details": details}}


CODES = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found", 405: "method_not_allowed",
         409: "conflict", 413: "payload_too_large", 415: "unsupported_media_type", 429: "rate_limited"}


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(_body(request, exc.code, exc.message, exc.details), status_code=exc.status)

    @app.exception_handler(CalculationInputError)
    async def _calc(request: Request, exc: CalculationInputError) -> JSONResponse:
        details = [{"field": e.field, "code": e.code, "message": e.message} for e in exc.errors]
        return JSONResponse(_body(request, "validation_error", "輸入資料不正確", details), status_code=422)

    @app.exception_handler(RequestValidationError)
    async def _val(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"field": ".".join(str(x) for x in e["loc"][1:]), "code": e["type"], "message": e["msg"]}
                   for e in exc.errors()]
        return JSONResponse(_body(request, "validation_error", "輸入資料不正確", details), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(_body(request, CODES.get(exc.status_code, "error"), str(exc.detail)),
                            status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _any(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error request_id=%s", getattr(request.state, "request_id", None))
        return JSONResponse(_body(request, "internal_error", "系統發生錯誤，請稍後再試"), status_code=500)
