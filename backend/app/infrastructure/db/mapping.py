"""Map between domain dataclasses and ORM rows.

ORM rows are not domain types. Mapping reconstructs domain objects so Decimal
and UTC validation run at the persistence boundary.
"""

from __future__ import annotations

from uuid import UUID

from app.domain.order import Fill, Order, OrderStatus, PositionSide
from app.domain.portfolio import PortfolioState
from app.domain.position import Position, PositionStatus
from app.domain.risk import RiskDecision, RiskVerdict
from app.domain.signal import Signal, SignalSide
from app.infrastructure.db.models import (
    FillRow,
    OrderRow,
    PortfolioSnapshotRow,
    PositionRow,
    RiskDecisionRow,
    SignalRow,
)


def metadata_to_json(pairs: tuple[tuple[str, str], ...]) -> list[list[str]]:
    return [list(pair) for pair in pairs]


def metadata_from_json(value: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list):
        raise TypeError("signal metadata_json must be a list of [key, value] pairs")
    pairs: list[tuple[str, str]] = []
    for item in value:
        if not isinstance(item, list) or len(item) != 2:
            raise TypeError("signal metadata_json entries must be [key, value]")
        key, raw = item
        if not isinstance(key, str) or not isinstance(raw, str):
            raise TypeError("signal metadata_json keys and values must be str")
        pairs.append((key, raw))
    return tuple(pairs)


def signal_to_row(signal: Signal) -> SignalRow:
    return SignalRow(
        signal_id=signal.signal_id,
        strategy_name=signal.strategy_name,
        strategy_version=signal.strategy_version,
        symbol=signal.symbol,
        timeframe=signal.timeframe,
        side=signal.side.value,
        trigger_price=signal.trigger_price,
        stop_model=signal.stop_model,
        exit_model=signal.exit_model,
        created_at=signal.created_at,
        dataset_hash=signal.dataset_hash,
        market_data_version=signal.market_data_version,
        metadata_json=metadata_to_json(signal.metadata),
    )


def signal_from_row(row: SignalRow) -> Signal:
    return Signal(
        signal_id=row.signal_id,
        strategy_name=row.strategy_name,
        strategy_version=row.strategy_version,
        symbol=row.symbol,
        timeframe=row.timeframe,
        side=SignalSide(row.side),
        trigger_price=row.trigger_price,
        stop_model=row.stop_model,
        exit_model=row.exit_model,
        created_at=row.created_at,
        dataset_hash=row.dataset_hash,
        market_data_version=row.market_data_version,
        metadata=metadata_from_json(row.metadata_json),
    )


def risk_decision_to_row(decision: RiskDecision) -> RiskDecisionRow:
    return RiskDecisionRow(
        decision_id=decision.decision_id,
        signal_id=decision.signal_id,
        verdict=decision.verdict.value,
        reason_codes=list(decision.reason_codes),
        calculated_size=decision.calculated_size,
        estimated_risk_usd=decision.estimated_risk_usd,
        estimated_risk_pct=decision.estimated_risk_pct,
        portfolio_open_risk_pct=decision.portfolio_open_risk_pct,
        created_at=decision.created_at,
    )


def risk_decision_from_row(row: RiskDecisionRow) -> RiskDecision:
    return RiskDecision(
        decision_id=row.decision_id,
        signal_id=row.signal_id,
        verdict=RiskVerdict(row.verdict),
        reason_codes=tuple(row.reason_codes),
        calculated_size=row.calculated_size,
        estimated_risk_usd=row.estimated_risk_usd,
        estimated_risk_pct=row.estimated_risk_pct,
        portfolio_open_risk_pct=row.portfolio_open_risk_pct,
        created_at=row.created_at,
    )


def order_to_row(order: Order) -> OrderRow:
    return OrderRow(
        order_id=order.order_id,
        client_order_id=order.client_order_id,
        symbol=order.symbol,
        side=order.side.value,
        quantity=order.quantity,
        filled_quantity=order.filled_quantity,
        status=order.status.value,
        created_at=order.created_at,
        signal_id=order.signal_id,
        risk_decision_id=order.risk_decision_id,
        exchange_order_id=order.exchange_order_id,
    )


def order_from_row(row: OrderRow) -> Order:
    return Order(
        order_id=row.order_id,
        client_order_id=row.client_order_id,
        symbol=row.symbol,
        side=PositionSide(row.side),
        quantity=row.quantity,
        filled_quantity=row.filled_quantity,
        status=OrderStatus(row.status),
        created_at=row.created_at,
        signal_id=row.signal_id,
        risk_decision_id=row.risk_decision_id,
        exchange_order_id=row.exchange_order_id,
    )


def fill_to_row(fill: Fill) -> FillRow:
    return FillRow(
        fill_id=fill.fill_id,
        order_id=fill.order_id,
        client_order_id=fill.client_order_id,
        quantity=fill.quantity,
        price=fill.price,
        fee=fill.fee,
        filled_at=fill.filled_at,
    )


def fill_from_row(row: FillRow) -> Fill:
    return Fill(
        fill_id=row.fill_id,
        order_id=row.order_id,
        client_order_id=row.client_order_id,
        quantity=row.quantity,
        price=row.price,
        fee=row.fee,
        filled_at=row.filled_at,
    )


def position_to_row(position: Position) -> PositionRow:
    return PositionRow(
        position_id=position.position_id,
        symbol=position.symbol,
        side=position.side.value,
        status=position.status.value,
        quantity=position.quantity,
        avg_entry_price=position.avg_entry_price,
        realized_pnl=position.realized_pnl,
        unrealized_pnl=position.unrealized_pnl,
        opened_at=position.opened_at,
    )


def position_from_row(row: PositionRow) -> Position:
    return Position(
        position_id=row.position_id,
        symbol=row.symbol,
        side=PositionSide(row.side),
        status=PositionStatus(row.status),
        quantity=row.quantity,
        avg_entry_price=row.avg_entry_price,
        realized_pnl=row.realized_pnl,
        unrealized_pnl=row.unrealized_pnl,
        opened_at=row.opened_at,
    )


def portfolio_to_row(state: PortfolioState, *, snapshot_id: UUID) -> PortfolioSnapshotRow:
    return PortfolioSnapshotRow(
        snapshot_id=snapshot_id,
        as_of=state.as_of,
        equity=state.equity,
        cash_balance=state.cash_balance,
        open_position_count=state.open_position_count,
        open_risk_pct=state.open_risk_pct,
        daily_realized_pnl=state.daily_realized_pnl,
        daily_unrealized_pnl=state.daily_unrealized_pnl,
    )


def portfolio_from_row(row: PortfolioSnapshotRow) -> PortfolioState:
    return PortfolioState(
        as_of=row.as_of,
        equity=row.equity,
        cash_balance=row.cash_balance,
        open_position_count=row.open_position_count,
        open_risk_pct=row.open_risk_pct,
        daily_realized_pnl=row.daily_realized_pnl,
        daily_unrealized_pnl=row.daily_unrealized_pnl,
    )
