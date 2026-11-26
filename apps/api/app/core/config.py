"""設定全部來自環境變數。密鑰只在後端。"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT / ".env", ROOT / "apps" / "api" / ".env"), extra="ignore")

    app_env: str = "development"
    demo_mode: bool = True
    web_url: str = "http://localhost:3000"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    database_url: str = "postgresql+psycopg://leverage:leverage_local_dev@127.0.0.1:54330/leverage"

    # 驗證：local = 本機示範帳號（後端簽發 Supabase 格式 JWT）；supabase = 驗證 Supabase Auth JWT
    auth_mode: str = "local"
    jwt_secret: str = "local-dev-only-change-me-0123456789abcdef"
    supabase_url: str | None = None
    supabase_jwt_secret: str | None = None
    supabase_service_role_key: str | None = None

    # AI：ollama（千問，本機）、gemini（需要金鑰）、none（只用規則與模板）
    llm_provider: str = "ollama"
    llm_model: str = "qwen3:8b"
    ollama_base_url: str = "http://127.0.0.1:11434"
    embedding_model: str | None = None
    google_api_key: str | None = None
    gemini_model: str | None = None
    llm_timeout_seconds: float = 180.0

    redis_url: str | None = None
    # 雲端 serverless（Vercel）：資料庫不用連線池、檔案存資料庫、Agent 在請求內同步完成
    serverless: bool = False
    storage_backend: str = "local"  # local | db
    agent_execution: str = "background"  # background | inline
    storage_dir: Path = ROOT / "apps" / "api" / "var" / "storage"  # serverless 請設為 /tmp/lg-storage
    max_upload_size: int = 10 * 1024 * 1024
    max_agent_iterations: int = 8
    max_analysis_cost: float = 0.5
    rate_limit_per_minute: int = 600
    legal_source_sync_enabled: bool = False
    regulatory_monitor_enabled: bool = True

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
