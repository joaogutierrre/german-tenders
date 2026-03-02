"""Database engine and session factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import settings

engine = create_async_engine(settings.database_url, echo=False)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session, committing on success and rolling back on error."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def reset_engine() -> None:
    """Dispose the current engine and recreate it.

    This is needed when ``asyncio.run()`` is called multiple times in the same
    process (e.g. the ``purge`` CLI command). Each ``asyncio.run()`` creates a
    new event loop, but the old engine keeps a reference to the closed loop.
    Calling ``reset_engine()`` between runs ensures a fresh connection pool.

    Simply creates a brand-new engine (the old one is abandoned). We do NOT
    call ``engine.dispose()`` because that tries to close asyncpg connections
    synchronously, raising MissingGreenlet errors.
    """
    global engine, async_session_factory
    engine = create_async_engine(settings.database_url, echo=False)
    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
