from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import async_engine

settings = get_settings()
configure_logging(debug=settings.debug)
logger = structlog.get_logger()

if settings.is_production and settings.sentry_dsn:  # type: ignore[attr-defined]
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.2)  # type: ignore[attr-defined]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", environment=settings.environment)
    async with async_engine.begin() as conn:
        # For development convenience; in production use Alembic migrations.
        # await conn.run_sync(Base.metadata.create_all)
        pass
    # Preload the local sentence-transformer embedding model once.
    try:
        from app.ai.embeddings import get_embedding_model

        get_embedding_model()
        logger.info("embedding_model_preloaded")
    except Exception as exc:
        logger.warning("embedding_model_preload_failed", error=str(exc))
    yield
    await async_engine.dispose()
    logger.info("app_shutting_down")


app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    description="AI-powered Europe job discovery for Senior DevOps / Platform Engineers",
    lifespan=lifespan,
    redirect_slashes=False,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok", "environment": settings.environment}


@app.get("/", include_in_schema=False)
async def root():
    return JSONResponse({"service": settings.project_name, "docs": "/docs"})
