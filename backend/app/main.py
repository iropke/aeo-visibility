from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import analyses, analysis, health, leads, members, sites, workspaces


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
    # v1 (legacy MVP) — v2 마이그레이션 002 적용 후 런타임 실패. 이후 제거 예정.
    app.include_router(analysis.router, prefix="/api", tags=["analysis"])
    app.include_router(leads.router, prefix="/api", tags=["leads"])
    # v2 라우터 (prefix는 라우터 자체에 포함됨).
    app.include_router(workspaces.router)
    app.include_router(members.router)
    app.include_router(sites.router)
    app.include_router(analyses.router)

    return app


app = create_app()
