"""Domain repositories. They map dataclasses through ORM rows; they are not domain types.

Callers must use these through ``UnitOfWork`` so commit/rollback stay explicit.
Do not hold a unit of work open across exchange or other network I/O.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fields import require_client_order_id
from app.domain.order import ORDER_TRANSITIONS, Fill, Order, OrderStatus
from app.domain.portfolio import PortfolioState
from app.domain.position import POSITION_TRANSITIONS, Position, PositionStatus
from app.domain.risk import RiskDecision
from app.domain.signal import Signal
from app.domain.state import assert_allowed_transition
from app.infrastructure.db.errors import map_integrity_error
from app.infrastructure.db.mapping import (
    apply_order_to_row,
    apply_position_to_row,
    fill_from_row,
    fill_to_row,
    order_from_row,
    order_to_row,
    portfolio_from_row,
    portfolio_to_row,
    position_from_row,
    position_to_row,
    risk_decision_from_row,
    risk_decision_to_row,
    signal_from_row,
    signal_to_row,
)
from app.infrastructure.db.models import (
    FillRow,
    OrderRow,
    PortfolioSnapshotRow,
    PositionRow,
    RiskDecisionRow,
    SignalRow,
)


class SignalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, signal: Signal) -> None:
        self._session.add(signal_to_row(signal))
        await _flush(self._session)

    async def get(self, signal_id: UUID) -> Signal | None:
        row = await self._session.get(SignalRow, signal_id)
        if row is None:
            return None
        return signal_from_row(row)


class RiskDecisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, decision: RiskDecision) -> None:
        self._session.add(risk_decision_to_row(decision))
        await _flush(self._session)

    async def get(self, decision_id: UUID) -> RiskDecision | None:
        row = await self._session.get(RiskDecisionRow, decision_id)
        if row is None:
            return None
        return risk_decision_from_row(row)


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, order: Order) -> None:
        self._session.add(order_to_row(order))
        await _flush(self._session)

    async def save(self, order: Order) -> None:
        """Insert or update. Status changes must follow ``ORDER_TRANSITIONS``."""

        row = await self._session.get(OrderRow, order.order_id)
        if row is None:
            self._session.add(order_to_row(order))
            await _flush(self._session)
            return
        current = OrderStatus(row.status)
        if current is not order.status:
            assert_allowed_transition("order", current, order.status, ORDER_TRANSITIONS)
        apply_order_to_row(row, order)
        await _flush(self._session)

    async def get(self, order_id: UUID) -> Order | None:
        row = await self._session.get(OrderRow, order_id)
        if row is None:
            return None
        return order_from_row(row)

    async def get_by_client_order_id(self, client_order_id: str) -> Order | None:
        identity = require_client_order_id(client_order_id)
        result = await self._session.execute(
            select(OrderRow).where(OrderRow.client_order_id == identity)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return order_from_row(row)


class FillRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, fill: Fill) -> None:
        self._session.add(fill_to_row(fill))
        await _flush(self._session)

    async def list_for_order(self, order_id: UUID) -> tuple[Fill, ...]:
        result = await self._session.execute(
            select(FillRow).where(FillRow.order_id == order_id).order_by(FillRow.filled_at)
        )
        return tuple(fill_from_row(row) for row in result.scalars())


class PositionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, position: Position) -> None:
        self._session.add(position_to_row(position))
        await _flush(self._session)

    async def save(self, position: Position) -> None:
        row = await self._session.get(PositionRow, position.position_id)
        if row is None:
            self._session.add(position_to_row(position))
            await _flush(self._session)
            return
        current = PositionStatus(row.status)
        if current is not position.status:
            assert_allowed_transition("position", current, position.status, POSITION_TRANSITIONS)
        apply_position_to_row(row, position)
        await _flush(self._session)

    async def get(self, position_id: UUID) -> Position | None:
        row = await self._session.get(PositionRow, position_id)
        if row is None:
            return None
        return position_from_row(row)


class PortfolioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, state: PortfolioState, *, snapshot_id: UUID | None = None) -> UUID:
        identity = uuid4() if snapshot_id is None else snapshot_id
        self._session.add(portfolio_to_row(state, snapshot_id=identity))
        await _flush(self._session)
        return identity

    async def get(self, snapshot_id: UUID) -> PortfolioState | None:
        row = await self._session.get(PortfolioSnapshotRow, snapshot_id)
        if row is None:
            return None
        return portfolio_from_row(row)


async def _flush(session: AsyncSession) -> None:
    try:
        await session.flush()
    except IntegrityError as error:
        raise map_integrity_error(error) from error
