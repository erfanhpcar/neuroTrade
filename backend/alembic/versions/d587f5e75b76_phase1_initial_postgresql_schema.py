"""phase1 initial postgresql schema

Revision ID: d587f5e75b76
Revises:
Create Date: 2026-08-27 19:06:43.566123
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d587f5e75b76"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_name", sa.Text(), nullable=False),
        sa.Column("strategy_version", sa.Text(), nullable=False),
        sa.Column("config_hash", sa.Text(), nullable=False),
        sa.Column("dataset_hash", sa.Text(), nullable=False),
        sa.Column("code_commit_sha", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("run_id", name=op.f("pk_backtest_runs")),
    )
    op.create_table(
        "portfolio_snapshots",
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("equity", sa.Numeric(), nullable=False),
        sa.Column("cash_balance", sa.Numeric(), nullable=False),
        sa.Column("open_position_count", sa.Integer(), nullable=False),
        sa.Column("open_risk_pct", sa.Numeric(), nullable=False),
        sa.Column("daily_realized_pnl", sa.Numeric(), nullable=False),
        sa.Column("daily_unrealized_pnl", sa.Numeric(), nullable=False),
        sa.CheckConstraint(
            "open_position_count >= 0",
            name=op.f("ck_portfolio_snapshots_open_position_count"),
        ),
        sa.PrimaryKeyConstraint("snapshot_id", name=op.f("pk_portfolio_snapshots")),
    )
    op.create_index(
        op.f("ix_portfolio_snapshots_as_of"),
        "portfolio_snapshots",
        ["as_of"],
        unique=False,
    )
    op.create_table(
        "positions",
        sa.Column("position_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(), nullable=False),
        sa.Column("avg_entry_price", sa.Numeric(), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("side IN ('LONG', 'SHORT')", name=op.f("ck_positions_side")),
        sa.CheckConstraint(
            "status IN ('OPENING', 'OPEN', 'CLOSING', 'CLOSED')",
            name=op.f("ck_positions_status"),
        ),
        sa.PrimaryKeyConstraint("position_id", name=op.f("pk_positions")),
    )
    op.create_table(
        "signals",
        sa.Column("signal_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_name", sa.Text(), nullable=False),
        sa.Column("strategy_version", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("timeframe", sa.Text(), nullable=False),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("trigger_price", sa.Numeric(), nullable=False),
        sa.Column("stop_model", sa.Text(), nullable=False),
        sa.Column("exit_model", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dataset_hash", sa.Text(), nullable=True),
        sa.Column("market_data_version", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "side IN ('LONG', 'SHORT', 'FLAT')",
            name=op.f("ck_signals_side"),
        ),
        sa.PrimaryKeyConstraint("signal_id", name=op.f("pk_signals")),
    )
    op.create_table(
        "strategy_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("config_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_strategy_versions")),
        sa.UniqueConstraint("name", "version", name="uq_strategy_versions_name_version"),
    )
    op.create_table(
        "system_events",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("event_id", name=op.f("pk_system_events")),
    )
    op.create_table(
        "system_settings",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_system_settings")),
    )
    op.create_table(
        "backtest_metrics",
        sa.Column("metric_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["backtest_runs.run_id"],
            name=op.f("fk_backtest_metrics_run_id_backtest_runs"),
        ),
        sa.PrimaryKeyConstraint("metric_id", name=op.f("pk_backtest_metrics")),
        sa.UniqueConstraint("run_id", "name", name="uq_backtest_metrics_run_id_name"),
    )
    op.create_index(
        op.f("ix_backtest_metrics_run_id"),
        "backtest_metrics",
        ["run_id"],
        unique=False,
    )
    op.create_table(
        "risk_decisions",
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("signal_id", sa.Uuid(), nullable=False),
        sa.Column("verdict", sa.Text(), nullable=False),
        sa.Column("reason_codes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("calculated_size", sa.Numeric(), nullable=False),
        sa.Column("estimated_risk_usd", sa.Numeric(), nullable=False),
        sa.Column("estimated_risk_pct", sa.Numeric(), nullable=False),
        sa.Column("portfolio_open_risk_pct", sa.Numeric(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "verdict IN ('APPROVED', 'REJECTED')",
            name=op.f("ck_risk_decisions_verdict"),
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.signal_id"],
            name=op.f("fk_risk_decisions_signal_id_signals"),
        ),
        sa.PrimaryKeyConstraint("decision_id", name=op.f("pk_risk_decisions")),
    )
    op.create_index(
        op.f("ix_risk_decisions_signal_id"),
        "risk_decisions",
        ["signal_id"],
        unique=False,
    )
    op.create_table(
        "orders",
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("client_order_id", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(), nullable=False),
        sa.Column("filled_quantity", sa.Numeric(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signal_id", sa.Uuid(), nullable=True),
        sa.Column("risk_decision_id", sa.Uuid(), nullable=True),
        sa.Column("exchange_order_id", sa.Text(), nullable=True),
        sa.CheckConstraint("side IN ('LONG', 'SHORT')", name=op.f("ck_orders_side")),
        sa.CheckConstraint(
            "status IN ('CREATED', 'RISK_APPROVED', 'SUBMITTING', 'SUBMITTED', "
            "'PARTIALLY_FILLED', 'FILLED', 'CANCELED', 'REJECTED', 'FAILED')",
            name=op.f("ck_orders_status"),
        ),
        sa.CheckConstraint(
            "char_length(btrim(client_order_id)) > 0",
            name=op.f("ck_orders_client_order_id_nonempty"),
        ),
        sa.ForeignKeyConstraint(
            ["risk_decision_id"],
            ["risk_decisions.decision_id"],
            name=op.f("fk_orders_risk_decision_id_risk_decisions"),
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.signal_id"],
            name=op.f("fk_orders_signal_id_signals"),
        ),
        sa.PrimaryKeyConstraint("order_id", name=op.f("pk_orders")),
        sa.UniqueConstraint("client_order_id", name="uq_orders_client_order_id"),
        sa.UniqueConstraint("exchange_order_id", name="uq_orders_exchange_order_id"),
    )
    op.create_table(
        "risk_events",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("signal_id", sa.Uuid(), nullable=True),
        sa.Column("decision_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["risk_decisions.decision_id"],
            name=op.f("fk_risk_events_decision_id_risk_decisions"),
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.signal_id"],
            name=op.f("fk_risk_events_signal_id_signals"),
        ),
        sa.PrimaryKeyConstraint("event_id", name=op.f("pk_risk_events")),
    )
    op.create_table(
        "fills",
        sa.Column("fill_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("client_order_id", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(), nullable=False),
        sa.Column("price", sa.Numeric(), nullable=False),
        sa.Column("fee", sa.Numeric(), nullable=False),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.order_id"],
            name=op.f("fk_fills_order_id_orders"),
        ),
        sa.PrimaryKeyConstraint("fill_id", name=op.f("pk_fills")),
    )
    op.create_index(op.f("ix_fills_client_order_id"), "fills", ["client_order_id"], unique=False)
    op.create_index(op.f("ix_fills_order_id"), "fills", ["order_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_fills_order_id"), table_name="fills")
    op.drop_index(op.f("ix_fills_client_order_id"), table_name="fills")
    op.drop_table("fills")
    op.drop_table("risk_events")
    op.drop_table("orders")
    op.drop_index(op.f("ix_risk_decisions_signal_id"), table_name="risk_decisions")
    op.drop_table("risk_decisions")
    op.drop_index(op.f("ix_backtest_metrics_run_id"), table_name="backtest_metrics")
    op.drop_table("backtest_metrics")
    op.drop_table("system_settings")
    op.drop_table("system_events")
    op.drop_table("strategy_versions")
    op.drop_table("signals")
    op.drop_table("positions")
    op.drop_index(op.f("ix_portfolio_snapshots_as_of"), table_name="portfolio_snapshots")
    op.drop_table("portfolio_snapshots")
    op.drop_table("backtest_runs")
