"""PostgreSQL helpers for migration integration tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from app.config import Settings
from app.infrastructure.db.engine import create_async_engine_from_url, redact_database_url

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def integration_database_url() -> str:
    explicit = os.environ.get("NEUROTRADE_TEST_DATABASE_URL")
    if explicit:
        return explicit
    if os.environ.get("GITHUB_ACTIONS") and os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    base = os.environ.get("DATABASE_URL") or Settings(_env_file=None).database_url
    return make_url(base).set(database="neurotrade_test").render_as_string(hide_password=False)


def alembic_config(database_url: str) -> Config:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def run_upgrade(database_url: str) -> None:
    os.environ["DATABASE_URL"] = database_url
    command.upgrade(alembic_config(database_url), "head")


def run_downgrade_base(database_url: str) -> None:
    os.environ["DATABASE_URL"] = database_url
    command.downgrade(alembic_config(database_url), "base")


async def reset_public_schema(database_url: str) -> None:
    engine = create_async_engine_from_url(database_url)
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
        await connection.execute(text("GRANT ALL ON SCHEMA public TO CURRENT_USER"))
        await connection.execute(text("GRANT ALL ON SCHEMA public TO public"))
    await engine.dispose()


async def postgres_is_reachable(database_url: str) -> bool:
    engine = create_async_engine_from_url(database_url)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except (OperationalError, OSError, ConnectionError):
        return False
    finally:
        await engine.dispose()


def require_postgres() -> str:
    import asyncio

    url = integration_database_url()
    reachable = asyncio.run(postgres_is_reachable(url))
    required = (
        os.environ.get("GITHUB_ACTIONS") == "true" or os.environ.get("NEUROTRADE_REQUIRE_DB") == "1"
    )
    if not reachable:
        message = f"PostgreSQL is not reachable at {redact_database_url(url)}"
        if required:
            pytest.fail(message)
        pytest.skip(message)
    return url
