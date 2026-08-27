"""Async engine helpers. Callers must dispose engines they create."""

from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def redact_database_url(database_url: str) -> str:
    """Return a log-safe URL with the password hidden."""

    return make_url(database_url).render_as_string(hide_password=True)


def create_async_engine_from_url(database_url: str) -> AsyncEngine:
    """Create an async SQLAlchemy engine for PostgreSQL/asyncpg."""

    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Session factory with explicit commit. Not a repository."""

    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
