from typing import Optional
from uuid import UUID

from redis.asyncio import from_url as redis_from_url

from app.config import get_settings

KEY_PREFIX = "aeo:result:"


async def _get_redis():
    settings = get_settings()
    return redis_from_url(settings.redis_url, decode_responses=True)


async def get_cached_result(domain: str) -> Optional[UUID]:
    r = await _get_redis()
    try:
        val = await r.get(f"{KEY_PREFIX}{domain}")
        return UUID(val) if val else None
    finally:
        await r.aclose()


async def set_cached_result(domain: str, analysis_id: str, ttl_days: int = 7):
    r = await _get_redis()
    try:
        await r.set(f"{KEY_PREFIX}{domain}", str(analysis_id), ex=ttl_days * 86400)
    finally:
        await r.aclose()
