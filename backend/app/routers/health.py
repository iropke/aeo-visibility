import asyncio

from fastapi import APIRouter
from redis.asyncio import from_url as redis_from_url
from sqlalchemy import text

from app.config import get_settings
from app.models.database import engine
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health")
async def health_check():
    settings = get_settings()
    db_status = "disconnected"
    db_error = None
    redis_status = "disconnected"
    redis_error = None

    # DB check with 5s timeout
    try:
        async with asyncio.timeout(5):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception as e:
        db_error = f"{type(e).__name__}: {str(e)[:200]}"

    # Redis check with 3s timeout
    try:
        async with asyncio.timeout(3):
            r = redis_from_url(settings.redis_url)
            await r.ping()
            await r.aclose()
            redis_status = "connected"
    except Exception as e:
        redis_error = f"{type(e).__name__}: {str(e)[:200]}"

    overall = "ok" if db_status == "connected" and redis_status == "connected" else "degraded"
    return {
        "status": overall,
        "db": db_status,
        "db_error": db_error,
        "redis": redis_status,
        "redis_error": redis_error,
    }
