from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import analysis, health, leads


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown: engine cleanup handled by SQLAlchemy


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AEO Visibility API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(analysis.router, prefix="/api", tags=["analysis"])
    app.include_router(leads.router, prefix="/api", tags=["leads"])

    return app


app = create_app()
