from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import settings


def build_engine() -> AsyncEngine | None:
    if not settings.DATABASE_URL:
        return None
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return create_async_engine(url, pool_pre_ping=True, pool_recycle=1800)


engine = build_engine()
SessionFactory = async_sessionmaker(engine, expire_on_commit=False) if engine is not None else None
