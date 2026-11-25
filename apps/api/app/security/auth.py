"""身分驗證與角色。

- AUTH_MODE=local：只允許示範帳號，由後端簽發 Supabase 格式（sub、role=authenticated）的 JWT，方便本機與黑客松展示。
- AUTH_MODE=supabase：驗證 Supabase Auth 簽發的 JWT（HS256，SUPABASE_JWT_SECRET）。
權限一律由後端判斷＋資料庫 RLS 強制，前端隱藏按鈕不算權限控制。
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Annotated, Any

import jwt
from fastapi import Depends, Request

from ..core.config import get_settings
from ..core.db import one, service_session
from ..core.errors import ApiError

DEMO_ACCOUNTS = [
    {"email": "investor@demo.leverageguard.local", "display_name": "示範投資人", "role": "investor",
     "id": "00000000-0000-4000-8000-000000000001"},
    {"email": "reviewer@demo.leverageguard.local", "display_name": "示範法律審查員", "role": "legal_reviewer",
     "id": "00000000-0000-4000-8000-000000000002"},
    {"email": "admin@demo.leverageguard.local", "display_name": "示範系統管理員", "role": "system_admin",
     "id": "00000000-0000-4000-8000-000000000003"},
    {"email": "investor2@demo.leverageguard.local", "display_name": "示範投資人二", "role": "investor",
     "id": "00000000-0000-4000-8000-000000000004"},
]


@dataclass
class Principal:
    id: str
    email: str
    role: str
    display_name: str
    claims: dict[str, Any]


def issue_local_token(user_id: str, email: str, ttl: int = 8 * 3600) -> tuple[str, int]:
    s = get_settings()
    now = int(time.time())
    claims = {"sub": user_id, "email": email, "role": "authenticated", "aud": "authenticated",
              "iat": now, "exp": now + ttl, "iss": "leverageguard-local"}
    return jwt.encode(claims, s.jwt_secret, algorithm="HS256"), ttl


def _decode(token: str) -> dict[str, Any]:
    s = get_settings()
    try:
        if s.auth_mode == "supabase":
            if not s.supabase_jwt_secret:
                raise ApiError(503, "not_configured", "尚未設定 SUPABASE_JWT_SECRET")
            return jwt.decode(token, s.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated")
        return jwt.decode(token, s.jwt_secret, algorithms=["HS256"], audience="authenticated",
                          issuer="leverageguard-local")
    except jwt.ExpiredSignatureError as e:
        raise ApiError(401, "unauthorized", "登入已過期，請重新登入") from e
    except jwt.PyJWTError as e:
        raise ApiError(401, "unauthorized", "登入憑證無效") from e


def ensure_profile(user_id: str, email: str, display_name: str, role: str = "investor") -> None:
    """建立 auth.users 與 profiles（只在本機模式或首次登入時）。"""
    with service_session() as conn:
        from sqlalchemy import text
        if get_settings().auth_mode == "local":
            conn.execute(text("insert into auth.users (id, email) values (:i, :e) on conflict (id) do nothing"),
                         {"i": user_id, "e": email})
        conn.execute(text("""insert into profiles (id, email, display_name, role) values (:i, :e, :n, :r)
                             on conflict (id) do nothing"""), {"i": user_id, "e": email, "n": display_name, "r": role})


def optional_principal(request: Request) -> Principal | None:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    claims = _decode(header[7:].strip())
    uid = claims.get("sub")
    try:
        uuid.UUID(str(uid))
    except ValueError as e:
        raise ApiError(401, "unauthorized", "登入憑證無效") from e
    with service_session() as conn:
        prof = one(conn, "select id::text, email, role, display_name from profiles where id = :i", i=uid)
    if prof is None:
        if get_settings().auth_mode == "supabase":
            ensure_profile(uid, claims.get("email", ""), (claims.get("email") or "使用者").split("@")[0])
            prof = {"id": uid, "email": claims.get("email", ""), "role": "investor", "display_name": "使用者"}
        else:
            raise ApiError(401, "unauthorized", "帳號不存在")
    request.state.user_id = uid
    return Principal(prof["id"], prof["email"], prof["role"], prof["display_name"], claims)


def require_principal(p: Annotated[Principal | None, Depends(optional_principal)]) -> Principal:
    if p is None:
        raise ApiError(401, "unauthorized", "請先登入")
    return p


def require_role(*roles: str):
    def dep(p: Annotated[Principal, Depends(require_principal)]) -> Principal:
        if p.role not in roles:
            raise ApiError(403, "forbidden", "沒有權限執行此操作")
        return p
    return dep


CurrentUser = Annotated[Principal, Depends(require_principal)]
MaybeUser = Annotated[Principal | None, Depends(optional_principal)]
