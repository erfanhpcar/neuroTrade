"""ORM table definitions for the documented Phase 1 PostgreSQL schema.

These rows are persistence records. Trading invariants are enforced by
``app.domain`` dataclasses when mapping in or out of the database.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.order import OrderStatus, PositionSide
from app.domain.position import PositionStatus
from app.domain.risk import RiskVerdict
from app.domain.signal import SignalSide
from app.infrastructure.db.base import Base

_ORDER_STATUS_SQL = ", ".join(f"'{item.value}'" for item in OrderStatus)
_POSITION_STATUS_SQL = ", ".join(f"'{item.value}'" for item in PositionStatus)
_POSITION_SIDE_SQL = ", ".join(f"'{item.value}'" for item in PositionSide)
_SIGNAL_SIDE_SQL = ", ".join(f"'{item.value}'" for item in SignalSide)
_RISK_VERDICT_SQL = ", ".join(f"'{item.value}'" for item in RiskVerdict)


class SystemSettingRow(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyVersionRow(Base):
    __tablename__ = "strategy_versions"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_strategy_versions_name_version"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    config_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SignalRow(Base):
    __tablename__ = "signals"
    __table_args__ = (CheckConstraint(f"side IN ({_SIGNAL_SIDE_SQL})", name="side"),)

    signal_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    strategy_name: Mapped[str] = mapped_column(Text, nullable=False)
    strategy_version: Mapped[str] = mapped_column(Text, nullable=False)
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    timeframe: Mapped[str] = mapped_column(Text, nullable=False)
    side: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_price: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    stop_model: Mapped[str] = mapped_column(Text, nullable=False)
    exit_model: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dataset_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    market_data_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Column is not named "metadata" because that clashes with SQLAlchemy MetaData.
    metadata_json: Mapped[list[list[str]]] = mapped_column(JSONB, nullable=False)


class RiskDecisionRow(Base):
    __tablename__ = "risk_decisions"
    __table_args__ = (CheckConstraint(f"verdict IN ({_RISK_VERDICT_SQL})", name="verdict"),)

    decision_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    signal_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("signals.signal_id"), nullable=False, index=True
    )
    verdict: Mapped[str] = mapped_column(Text, nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    calculated_size: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    estimated_risk_usd: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    estimated_risk_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    portfolio_open_risk_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrderRow(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("client_order_id", name="uq_orders_client_order_id"),
        UniqueConstraint("exchange_order_id", name="uq_orders_exchange_order_id"),
        CheckConstraint("char_length(btrim(client_order_id)) > 0", name="client_order_id_nonempty"),
        CheckConstraint(f"status IN ({_ORDER_STATUS_SQL})", name="status"),
        CheckConstraint(f"side IN ({_POSITION_SIDE_SQL})", name="side"),
    )

    order_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    client_order_id: Mapped[str] = mapped_column(Text, nullable=False)
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    side: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    filled_quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    signal_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("signals.signal_id"), nullable=True
    )
    risk_decision_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("risk_decisions.decision_id"), nullable=True
    )
    exchange_order_id: Mapped[str | None] = mapped_column(Text, nullable=True)


class FillRow(Base):
    __tablename__ = "fills"

    fill_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    order_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("orders.order_id"), nullable=False, index=True
    )
    client_order_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    filled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PositionRow(Base):
    __tablename__ = "positions"
    __table_args__ = (
        CheckConstraint(f"status IN ({_POSITION_STATUS_SQL})", name="status"),
        CheckConstraint(f"side IN ({_POSITION_SIDE_SQL})", name="side"),
    )

    position_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    side: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    avg_entry_price: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PortfolioSnapshotRow(Base):
    __tablename__ = "portfolio_snapshots"
    __table_args__ = (CheckConstraint("open_position_count >= 0", name="open_position_count"),)

    snapshot_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    equity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    open_position_count: Mapped[int] = mapped_column(Integer, nullable=False)
    open_risk_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    daily_realized_pnl: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    daily_unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric, nullable=False)


class RiskEventRow(Base):
    __tablename__ = "risk_events"

    event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    signal_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("signals.signal_id"), nullable=True
    )
    decision_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("risk_decisions.decision_id"), nullable=True
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestRunRow(Base):
    __tablename__ = "backtest_runs"

    run_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    strategy_name: Mapped[str] = mapped_column(Text, nullable=False)
    strategy_version: Mapped[str] = mapped_column(Text, nullable=False)
    config_hash: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_hash: Mapped[str] = mapped_column(Text, nullable=False)
    code_commit_sha: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestMetricRow(Base):
    __tablename__ = "backtest_metrics"
    __table_args__ = (UniqueConstraint("run_id", "name", name="uq_backtest_metrics_run_id_name"),)

    metric_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("backtest_runs.run_id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric, nullable=False)


class SystemEventRow(Base):
    __tablename__ = "system_events"

    event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


DOCUMENTED_TABLES: tuple[str, ...] = (
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
