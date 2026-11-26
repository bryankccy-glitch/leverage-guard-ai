"""Supabase 帳號密碼登入的憑證驗證（AUTH_MODE=supabase，新版 ES256 簽章）。不連網路、不需要資料庫。"""
from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.config import get_settings
from app.core.errors import ApiError
from app.security import auth

KEY = ec.generate_private_key(ec.SECP256R1())
OTHER = ec.generate_private_key(ec.SECP256R1())


class _FakeJwks:
    def get_signing_key_from_jwt(self, token):
        return jwt.PyJWK.from_dict(jwt.algorithms.ECAlgorithm.to_jwk(KEY.public_key(), as_dict=True) | {"alg": "ES256"})


@pytest.fixture
def supabase_mode(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("AUTH_MODE", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.setattr(auth, "_jwks_client", lambda url: _FakeJwks())
    yield
    get_settings.cache_clear()


def _token(key=KEY, **over):
    now = int(time.time())
    claims = {"sub": "11111111-1111-4111-8111-111111111111", "email": "bryan@leverageguard.local",
              "aud": "authenticated", "role": "authenticated", "iat": now, "exp": now + 3600} | over
    return jwt.encode(claims, key, algorithm="ES256")


def test_valid_es256_token_is_accepted(supabase_mode):
    claims = auth._decode(_token())
    assert claims["email"] == "bryan@leverageguard.local"


def test_token_signed_by_other_key_is_rejected(supabase_mode):
    with pytest.raises(ApiError) as e:
        auth._decode(_token(OTHER))
    assert e.value.status == 401


def test_expired_token_is_rejected(supabase_mode):
    with pytest.raises(ApiError) as e:
        auth._decode(_token(exp=int(time.time()) - 10))
    assert e.value.status == 401


def test_local_demo_token_is_rejected_in_supabase_mode(supabase_mode):
    # 切到 supabase 模式後，舊的示範登入憑證（HS256、本機簽發）不能再用
    get_settings.cache_clear()
    token, _ = auth.issue_local_token("00000000-0000-4000-8000-000000000003", "admin@demo.leverageguard.local")
    with pytest.raises(ApiError) as e:
        auth._decode(token)
    assert e.value.status == 401


def test_auth_config_exposes_login_domain_but_no_demo_accounts(supabase_mode, monkeypatch):
    monkeypatch.setenv("SUPABASE_ANON_KEY", "public-anon-key")
    get_settings.cache_clear()
    from app.api.public import auth_config
    cfg = auth_config()
    assert cfg["mode"] == "supabase"
    assert cfg["demo_accounts"] == []
    assert cfg["login_domain"] == "leverageguard.local"
    assert cfg["supabase_anon_key"] == "public-anon-key"
