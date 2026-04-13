from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Supabase
    database_url: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # Redis (caching)
    redis_url: str

    # AI APIs
    claude_api_key: str
    openai_api_key: str = ""

    # Email
    resend_api_key: str = ""

    # Frontend
    frontend_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"

    # Environment
    env: str = "development"
    log_level: str = "info"

    # Timeouts & Cache
    analysis_timeout_seconds: int = 30
    cache_ttl_days: int = 7

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
