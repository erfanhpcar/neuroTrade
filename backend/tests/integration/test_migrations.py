import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.domain.order import Order, OrderStatus, PositionSide
from app.infrastructure.db.engine import create_async_engine_from_url, create_session_factory
from app.infrastructure.db.mapping import order_from_row, order_to_row
from app.infrastructure.db.models import DOCUMENTED_TABLES, OrderRow
from tests.integration.db_support import (
    require_postgres,
    reset_public_schema,
    run_downgrade_base,
    run_upgrade,
)


def _utc() -> datetime:
    return datetime(2026, 8, 27, 12, 0, tzinfo=UTC)


def _created_order(*, client_order_id: str) -> Order:
    return Order(
        order_id=uuid4(),
        client_order_id=client_order_id,
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        quantity=Decimal("0.010"),
        filled_quantity=Decimal("0"),
        status=OrderStatus.CREATED,
        created_at=_utc(),
    )


async def _table_names(database_url: str) -> set[str]:
    engine = create_async_engine_from_url(database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            return {row[0] for row in result}
    finally:
        await engine.dispose()


def test_upgrade_from_empty_creates_documented_tables(migrated_database_url: str) -> None:
    tables = asyncio.run(_table_names(migrated_database_url))
    assert set(DOCUMENTED_TABLES).issubset(tables)
    assert "alembic_version" in tables


def test_orders_client_order_id_unique_in_postgres(migrated_database_url: str) -> None:
    async def _run() -> None:
        engine = create_async_engine_from_url(migrated_database_url)
        factory = create_session_factory(engine)
        try:
            async with factory() as session:
                session.add(order_to_row(_created_order(client_order_id="nt-dup-1")))
                await session.commit()
            async with factory() as session:
                session.add(order_to_row(_created_order(client_order_id="nt-dup-1")))
                with pytest.raises(IntegrityError, match="uq_orders_client_order_id"):
                    await session.commit()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_numeric_money_round_trip_through_postgres(migrated_database_url: str) -> None:
    original = Order(
        order_id=uuid4(),
        client_order_id="nt-decimal-1",
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        quantity=Decimal("0.00000001"),
        filled_quantity=Decimal("0"),
        status=OrderStatus.CREATED,
        created_at=_utc(),
    )

    async def _run() -> Order:
        engine = create_async_engine_from_url(migrated_database_url)
        factory = create_session_factory(engine)
        try:
            async with factory() as session:
                session.add(order_to_row(original))
                await session.commit()
            async with factory() as session:
                row = await session.get(OrderRow, original.order_id)
                assert row is not None
                return order_from_row(row)
        finally:
            await engine.dispose()

    restored = asyncio.run(_run())
    assert restored.quantity == Decimal("0.00000001")
    assert restored == original
    assert not isinstance(restored.quantity, float)


def test_downgrade_then_upgrade_recovers_schema() -> None:
    url = require_postgres()
    asyncio.run(reset_public_schema(url))
    run_upgrade(url)
    assert set(DOCUMENTED_TABLES).issubset(asyncio.run(_table_names(url)))

    run_downgrade_base(url)
    remaining = asyncio.run(_table_names(url))
    assert remaining.isdisjoint(DOCUMENTED_TABLES)

    run_upgrade(url)
    recovered = asyncio.run(_table_names(url))
    assert set(DOCUMENTED_TABLES).issubset(recovered)
    assert "alembic_version" in recovered
