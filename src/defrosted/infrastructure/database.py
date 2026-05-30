"""
Async SQLAlchemy engine + session factory.

One engine per process (pooled). Sessions are created per request/unit-of-work
and injected into repositories so multiple repos share one transaction.

Karpathy rule: explicit lifecycle. The engine is created once via
``init_engine`` and torn down via ``dispose_engine`` — no module-level magic
that connects to Postgres on import.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..config import Settings

# Created in init_engine(). We keep these at module scope because there is
# exactly one engine per process and it is read-only after startup.
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(settings: Settings) -> AsyncEngine:
    """Create the process-wide async engine and session factory. Idempotent."""
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
        )
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


async def dispose_engine() -> None:
    """Dispose the engine on shutdown. Safe to call when never initialized."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Yield a session bound to one unit of work, committing on success and
    rolling back on error. Use as a FastAPI dependency.
    """
    if _session_factory is None:
        raise RuntimeError("Database engine not initialized — call init_engine() at startup.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """
    Context-manager form of :func:`get_session` for use outside FastAPI
    (Temporal activities, scripts). Commits on success, rolls back on error.
    """
    if _session_factory is None:
        raise RuntimeError("Database engine not initialized — call init_engine() at startup.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
