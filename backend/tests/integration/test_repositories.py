"""PostgreSQL repository and unit-of-work tests.

These require a reachable database (same helper as migration tests).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.domain.errors import InvalidStateTransition
from app.domain.order import Fill, Order, OrderStatus, PositionSide
from app.domain.portfolio import PortfolioState
from app.domain.position import Position, PositionStatus
from app.domain.risk import RiskDecision, RiskVerdict
from app.domain.signal import Signal, SignalSide
from app.infrastructure.db.engine import create_async_engine_from_url, create_session_factory
from app.infrastructure.db.errors import DuplicateClientOrderId, PersistenceError
from app.infrastructure.db.unit_of_work import UnitOfWork


def _utc() -> datetime:
    return datetime(2026, 8, 27, 12, 0, tzinfo=UTC)


def _signal() -> Signal:
    return Signal(
        signal_id=uuid4(),
        strategy_name="trend_v1",
        strategy_version="1.0.0",
        symbol="BTC/USDT",
        timeframe="4h",
        side=SignalSide.LONG,
        trigger_price=Decimal("65000.50"),
        stop_model="atr_multiple",
        exit_model="trailing_atr",
        created_at=_utc(),
        metadata=(("regime", "trend"),),
    )


def _decision_for(signal: Signal) -> RiskDecision:
    return RiskDecision(
        decision_id=uuid4(),
        signal_id=signal.signal_id,
        verdict=RiskVerdict.APPROVED,
        reason_codes=(),
        calculated_size=Decimal("0.01"),
        estimated_risk_usd=Decimal("10.00"),
        estimated_risk_pct=Decimal("0.005"),
        portfolio_open_risk_pct=Decimal("0.01"),
        created_at=_utc(),
    )


def _order(
    *,
    client_order_id: str,
    signal_id: UUID | None = None,
    risk_decision_id: UUID | None = None,
) -> Order:
    return Order(
        order_id=uuid4(),
        client_order_id=client_order_id,
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        quantity=Decimal("0.010"),
        filled_quantity=Decimal("0"),
        status=OrderStatus.CREATED,
        created_at=_utc(),
        signal_id=signal_id,
        risk_decision_id=risk_decision_id,
    )


async def _with_uow(database_url: str, callback):
    engine = create_async_engine_from_url(database_url)
    factory = create_session_factory(engine)
    try:
        return await callback(factory)
    finally:
        await engine.dispose()


def test_uow_commit_persists_signal_risk_and_order(migrated_database_url: str) -> None:
    signal = _signal()
    decision = _decision_for(signal)
    order = _order(
        client_order_id="nt-uow-1",
        signal_id=signal.signal_id,
        risk_decision_id=decision.decision_id,
    )

    async def _run(factory) -> tuple[Signal | None, RiskDecision | None, Order | None]:
        async with UnitOfWork(factory) as uow:
            await uow.signals.add(signal)
            await uow.risk_decisions.add(decision)
            await uow.orders.add(order)
            await uow.commit()
        async with UnitOfWork(factory) as uow:
            loaded_signal = await uow.signals.get(signal.signal_id)
            loaded_decision = await uow.risk_decisions.get(decision.decision_id)
            loaded_order = await uow.orders.get_by_client_order_id("nt-uow-1")
            return loaded_signal, loaded_decision, loaded_order

    loaded_signal, loaded_decision, loaded_order = asyncio.run(
        _with_uow(migrated_database_url, _run)
    )
    assert loaded_signal == signal
    assert loaded_decision == decision
    assert loaded_order == order
    assert loaded_order is not None
    assert loaded_order.quantity == Decimal("0.010")
    assert not isinstance(loaded_order.quantity, float)


def test_uow_without_commit_rolls_back(migrated_database_url: str) -> None:
    signal = _signal()

    async def _run(factory) -> Signal | None:
        async with UnitOfWork(factory) as uow:
            await uow.signals.add(signal)
        async with UnitOfWork(factory) as uow:
            return await uow.signals.get(signal.signal_id)

    assert asyncio.run(_with_uow(migrated_database_url, _run)) is None


def test_uow_exception_rolls_back_signal_and_order(migrated_database_url: str) -> None:
    signal = _signal()
    order = _order(client_order_id="nt-uow-rollback")

    async def _run(factory) -> tuple[Signal | None, Order | None]:
        with pytest.raises(RuntimeError, match="pipeline failed"):
            async with UnitOfWork(factory) as uow:
                await uow.signals.add(signal)
                await uow.orders.add(order)
                raise RuntimeError("pipeline failed")
        async with UnitOfWork(factory) as uow:
            return await uow.signals.get(signal.signal_id), await uow.orders.get(order.order_id)

    loaded_signal, loaded_order = asyncio.run(_with_uow(migrated_database_url, _run))
    assert loaded_signal is None
    assert loaded_order is None


def test_duplicate_client_order_id_is_repository_error(migrated_database_url: str) -> None:
    first = _order(client_order_id="nt-uow-dup")
    second = _order(client_order_id="nt-uow-dup")

    async def _run(factory) -> None:
        async with UnitOfWork(factory) as uow:
            await uow.orders.add(first)
            await uow.commit()
        with pytest.raises(DuplicateClientOrderId, match="nt-uow-dup"):
            async with UnitOfWork(factory) as uow:
                await uow.orders.add(second)
                await uow.commit()
        async with UnitOfWork(factory) as uow:
            loaded = await uow.orders.get_by_client_order_id("nt-uow-dup")
            assert loaded == first

    asyncio.run(_with_uow(migrated_database_url, _run))


def test_order_save_rejects_invalid_status_skip(migrated_database_url: str) -> None:
    order = _order(client_order_id="nt-uow-skip")

    async def _run(factory) -> None:
        async with UnitOfWork(factory) as uow:
            await uow.orders.add(order)
            await uow.commit()
        skipped = Order(
            order_id=order.order_id,
            client_order_id=order.client_order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_quantity=order.filled_quantity,
            status=OrderStatus.SUBMITTED,
            created_at=order.created_at,
        )
        with pytest.raises(InvalidStateTransition, match="CREATED -> SUBMITTED"):
            async with UnitOfWork(factory) as uow:
                await uow.orders.save(skipped)
                await uow.commit()
        async with UnitOfWork(factory) as uow:
            loaded = await uow.orders.get(order.order_id)
            assert loaded == order

    asyncio.run(_with_uow(migrated_database_url, _run))


def test_order_save_persists_allowed_transition_and_fill(migrated_database_url: str) -> None:
    order = _order(client_order_id="nt-uow-fill")
    approved = order.transition(OrderStatus.RISK_APPROVED)
    fill = Fill(
        fill_id=uuid4(),
        order_id=order.order_id,
        client_order_id=order.client_order_id,
        quantity=Decimal("0.004"),
        price=Decimal("65000.25"),
        fee=Decimal("0.01"),
        filled_at=_utc(),
    )

    async def _run(factory) -> tuple[Order | None, tuple[Fill, ...]]:
        async with UnitOfWork(factory) as uow:
            await uow.orders.add(order)
            await uow.orders.save(approved)
            await uow.fills.add(fill)
            await uow.commit()
        async with UnitOfWork(factory) as uow:
            loaded = await uow.orders.get_by_client_order_id("nt-uow-fill")
            fills = await uow.fills.list_for_order(order.order_id)
            return loaded, fills

    loaded, fills = asyncio.run(_with_uow(migrated_database_url, _run))
    assert loaded == approved
    assert fills == (fill,)
    assert fills[0].price == Decimal("65000.25")
    assert not isinstance(fills[0].fee, float)


def test_position_and_portfolio_round_trip(migrated_database_url: str) -> None:
    position = Position(
        position_id=uuid4(),
        symbol="BTC/USDT",
        side=PositionSide.SHORT,
        status=PositionStatus.OPENING,
        quantity=Decimal("0.25"),
        avg_entry_price=Decimal("64000"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("0"),
        opened_at=_utc(),
    )
    opened = position.transition(PositionStatus.OPEN)
    state = PortfolioState(
        as_of=_utc(),
        equity=Decimal("10000.00"),
        cash_balance=Decimal("9999.50"),
        open_position_count=1,
        open_risk_pct=Decimal("0.02"),
        daily_realized_pnl=Decimal("-12.5"),
        daily_unrealized_pnl=Decimal("3"),
    )

    async def _run(factory) -> tuple[Position | None, PortfolioState | None]:
        async with UnitOfWork(factory) as uow:
            await uow.positions.add(position)
            await uow.positions.save(opened)
            snapshot_id = await uow.portfolio.add(state)
            await uow.commit()
        async with UnitOfWork(factory) as uow:
            return await uow.positions.get(position.position_id), await uow.portfolio.get(
                snapshot_id
            )

    loaded_position, loaded_state = asyncio.run(_with_uow(migrated_database_url, _run))
    assert loaded_position == opened
    assert loaded_state == state


def test_commit_after_close_is_rejected(migrated_database_url: str) -> None:
    async def _run(factory) -> None:
        uow = UnitOfWork(factory)
        async with uow:
            await uow.commit()
        with pytest.raises(PersistenceError, match="not active"):
            await uow.commit()

    asyncio.run(_with_uow(migrated_database_url, _run))
