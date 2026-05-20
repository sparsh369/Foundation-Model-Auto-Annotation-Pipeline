"""Async (API) and sync (worker/Alembic) SQLAlchemy session factories."""
from __future__ import annotations

from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import settings

# ── Async engine (FastAPI request path) ──────────────────────────
async_engine = create_async_engine(
    settings.async_database_url,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    echo=settings.debug,
)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

# ── Sync engine (Celery workers, migrations) ─────────────────────
sync_engine = create_engine(settings.sync_database_url, pool_pre_ping=True, pool_size=10)
SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async session with commit/rollback semantics."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_sync_db() -> Generator[Session, None, None]:
    """Context-style sync session for workers."""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
