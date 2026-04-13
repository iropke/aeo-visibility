from fastapi import APIRouter
from redis.asyncio import from_url as redis_from_url
from sqlalchemy import text

from app.config import get_settings
from app.models.database import engine
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    settings = get_settings()
    db_status = "disconnected"
    redis_status = "disconnected"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        pass

    try:
        r = redis_from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        redis_status = "connected"
    except Exception:
        pass

    overall = "ok" if db_status == "connected" and redis_status == "connected" else "degraded"
    return HealthResponse(status=overall, redis=redis_status, db=db_status)
