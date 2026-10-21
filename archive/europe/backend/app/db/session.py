from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Async engine for FastAPI
async_engine = create_async_engine(str(settings.database_url), echo=settings.debug)
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Sync engine for Celery, Alembic, scripts
sync_engine = create_engine(str(settings.database_url_sync), echo=settings.debug)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
