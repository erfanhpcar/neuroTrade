from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Numeric, UniqueConstraint

from app.domain.order import Order, OrderStatus, PositionSide
from app.domain.portfolio import PortfolioState
from app.domain.position import Position, PositionStatus
from app.domain.risk import RiskDecision, RiskVerdict
from app.domain.signal import Signal, SignalSide
from app.infrastructure.db.mapping import (
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
from app.infrastructure.db.models import DOCUMENTED_TABLES, FillRow, OrderRow, SignalRow


def _utc() -> datetime:
    return datetime(2026, 8, 27, 12, 0, tzinfo=UTC)


def test_documented_tables_are_declared() -> None:
    assert DOCUMENTED_TABLES == (
        "system_settings",
        "strategy_versions",
        "signals",
        "risk_decisions",
        "orders",
        "fills",
        "positions",
        "portfolio_snapshots",
        "risk_events",
        "backtest_runs",
        "backtest_metrics",
        "system_events",
    )


def test_orders_client_order_id_has_unique_constraint() -> None:
    names = {
        constraint.name
        for constraint in OrderRow.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_orders_client_order_id" in names


def test_money_columns_use_numeric_not_float() -> None:
    for column in (
        OrderRow.__table__.c.quantity,
        OrderRow.__table__.c.filled_quantity,
        FillRow.__table__.c.price,
        FillRow.__table__.c.fee,
        SignalRow.__table__.c.trigger_price,
    ):
        assert isinstance(column.type, Numeric)


def test_order_mapping_round_trip_preserves_decimal() -> None:
    order = Order(
        order_id=uuid4(),
        client_order_id="nt-client-1",
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        quantity=Decimal("0.010"),
        filled_quantity=Decimal("0"),
        status=OrderStatus.CREATED,
        created_at=_utc(),
    )
    restored = order_from_row(order_to_row(order))
    assert restored == order
    assert restored.quantity == Decimal("0.010")
    assert not isinstance(restored.quantity, float)


def test_signal_and_risk_mapping_round_trip() -> None:
    signal = Signal(
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
    restored_signal = signal_from_row(signal_to_row(signal))
    assert restored_signal == signal

    decision = RiskDecision(
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
    assert risk_decision_from_row(risk_decision_to_row(decision)) == decision


def test_position_and_portfolio_mapping_round_trip() -> None:
    position = Position(
        position_id=uuid4(),
        symbol="BTC/USDT",
        side=PositionSide.SHORT,
        status=PositionStatus.OPEN,
        quantity=Decimal("0.25"),
        avg_entry_price=Decimal("64000"),
        realized_pnl=Decimal("-1.5"),
        unrealized_pnl=Decimal("2.25"),
        opened_at=_utc(),
    )
    assert position_from_row(position_to_row(position)) == position

    state = PortfolioState(
        as_of=_utc(),
        equity=Decimal("10000.00"),
        cash_balance=Decimal("9999.50"),
        open_position_count=1,
        open_risk_pct=Decimal("0.02"),
        daily_realized_pnl=Decimal("-12.5"),
        daily_unrealized_pnl=Decimal("3"),
    )
    snapshot_id = uuid4()
    restored = portfolio_from_row(portfolio_to_row(state, snapshot_id=snapshot_id))
    assert restored == state
