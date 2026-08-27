"""Best-effort connectivity checks for external dependencies.

Phase 0 only needs to prove that PostgreSQL and Redis are reachable. These checks
are deliberately non-fatal: a failed dependency is reported as ``down`` rather than
raising, so the health endpoint can describe partial availability.
"""

from __future__ import annotations

import asyncpg
import redis.asyncio as redis

from app.config import Settings


async def check_postgres(settings: Settings, timeout: float = 2.0) -> bool:
    """Return ``True`` when a trivial query against PostgreSQL succeeds."""
    try:
        conn = await asyncpg.connect(dsn=settings.asyncpg_dsn, timeout=timeout)
    except (OSError, asyncpg.PostgresError):
        return False
    try:
        await conn.execute("SELECT 1;")
        return True
    except asyncpg.PostgresError:
        return False
    finally:
        await conn.close()


async def check_redis(settings: Settings, timeout: float = 2.0) -> bool:
    """Return ``True`` when Redis responds to ``PING``."""
    client = redis.from_url(
        settings.redis_url,
        socket_connect_timeout=timeout,
        socket_timeout=timeout,
    )
    try:
        return bool(await client.ping())
    except (OSError, redis.RedisError):
        return False
    finally:
        await client.aclose()
