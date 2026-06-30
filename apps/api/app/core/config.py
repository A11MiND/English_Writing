from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = "English AI Writing Platform"
    environment: str = "local"
    database_url: str = Field(
        default="postgresql+asyncpg://english_ai:english_ai_password@localhost:5432/english_ai_writing"
    )
    database_pool_enabled: bool = False
    redis_url: str = "redis://localhost:6379/0"
    marking_queue_name: str = "marking:jobs"
    marking_worker_poll_timeout_seconds: int = 5
    openauth_token_url: str | None = None
    openauth_userinfo_url: str | None = None
    openauth_client_id: str | None = None
    openauth_client_secret: str | None = None
    openauth_scope: str = "openid profile email"
    openauth_user_id_claim: str = "sub"
    openauth_school_id_claim: str = "school_id"
    openauth_role_claim: str = "role"
    grammar_provider: str = "languagetool"
    grammar_service_url: str | None = "http://grammar-service:8010"
    grammar_cache_ttl_seconds: int = 86_400
    api_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    session_cookie_name: str = "eaiwp_session"
    session_ttl_hours: int = 8
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"
    llm_provider: str = "deepseek"
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_timeout_seconds: float = 30.0

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
