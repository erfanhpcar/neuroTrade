"""Explicit unit of work around one PostgreSQL transaction.

Callers must ``commit()`` to persist. Exiting without commit, or with an
exception, rolls back. Do not keep a unit of work open across exchange or
other network I/O — persist locally, then talk to the network, then open a
new unit of work if needed.
"""

from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.errors import PersistenceError, map_integrity_error
from app.infrastructure.db.repositories import (
    FillRepository,
    OrderRepository,
    PortfolioRepository,
    PositionRepository,
    RiskDecisionRepository,
    SignalRepository,
)


class UnitOfWork:
    """One database transaction with trading repositories."""

    signals: SignalRepository
    risk_decisions: RiskDecisionRepository
    orders: OrderRepository
    fills: FillRepository
    positions: PositionRepository
    portfolio: PortfolioRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._committed = False

    async def __aenter__(self) -> Self:
        if self._session is not None:
            raise PersistenceError("unit of work is already active")
        self._session = self._session_factory()
        await self._session.begin()
        self.signals = SignalRepository(self._session)
        self.risk_decisions = RiskDecisionRepository(self._session)
        self.orders = OrderRepository(self._session)
        self.fills = FillRepository(self._session)
        self.positions = PositionRepository(self._session)
        self.portfolio = PortfolioRepository(self._session)
        return self

    async def commit(self) -> None:
        session = self._require_session()
        if self._committed:
            raise PersistenceError("unit of work already committed")
        try:
            await session.commit()
        except IntegrityError as error:
            await session.rollback()
            raise map_integrity_error(error) from error
        self._committed = True

    async def rollback(self) -> None:
        session = self._session
        if session is None:
            return
        if session.in_transaction():
            await session.rollback()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if self._session is not None and not self._committed:
                await self.rollback()
        finally:
            if self._session is not None:
                await self._session.close()
            self._session = None

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise PersistenceError("unit of work is not active")
        return self._session
