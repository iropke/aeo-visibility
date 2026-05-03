from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Supabase
    database_url: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str = ""  # v2 Auth: JWT 검증용. 빈 값이면 인증 의존성에서 명시적 에러.

    # Redis (caching)
    redis_url: str

    # AI APIs
    claude_api_key: str
    openai_api_key: str = ""

    # LLM Synthesizer (services/llm_synthesizer)
    # G6 청크: 5축 메트릭 통합 → insights/improvements 합성용 단일 모델.
    # Phase 1 단일 string. Phase 2 에 per-tier dict 확장 시 1줄 refactor.
    # Visibility 카테고리의 Haiku 호출 (claude_api_key) 과는 분리된 레이어.
    synthesizer_model: str = "claude-sonnet-4-6"

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
