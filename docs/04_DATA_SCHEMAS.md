# 04 — Data & Persistence

## PostgreSQL

جداول اصلی:

```text
system_settings
strategy_versions
signals
risk_decisions
orders
fills
positions
portfolio_snapshots
risk_events
backtest_runs
backtest_metrics
system_events
```

## اصول schema

- همه timestampها UTC.
- money/price/quantity با Decimal/NUMERIC؛ float برای persistence ممنوع.
- هر entity معاملاتی UUID داخلی دارد.
- `client_order_id` یکتا و index شده است.
- exchange identifiers جدا از ID داخلی ذخیره می‌شوند.
- state transitionها audit شوند.

## In-memory domain models (Phase 1)

Framework-independent dataclasses live in `backend/app/domain/`. They are not SQLAlchemy models. Persistence rows live in `backend/app/infrastructure/db/` and map to these dataclasses.

Financial fields are `Decimal`. Wire/JSON serialization uses decimal **strings** (`decimal_to_text`), never binary floats. PostgreSQL stores money as `NUMERIC` (unbounded precision). Timestamps are timezone-aware UTC (`TIMESTAMPTZ`). Trading entities use UUID primary identities. `client_order_id` is required on `OrderIntent`, `Order`, and `Fill`; uniqueness is enforced by `uq_orders_client_order_id` on `orders`.

`Signal` has no `position_size`. Final size belongs on `RiskDecision.calculated_size` and then `OrderIntent.quantity`.

`OrderIntent` / `Order` / `Position` use `PositionSide` `LONG` | `SHORT`. Mapping to exchange `BUY`/`SELL` is an Execution concern (Phase 6). Order type (`MARKET`/`LIMIT`) is not modeled yet. `OrderIntent` is a domain handoff object and does **not** have its own table.

Historical OHLCV/`MarketSnapshot` is not stored in PostgreSQL.

## PostgreSQL table columns (Phase 1 persistence)

Alembic revision `d587f5e75b76` creates the documented tables. ORM rows are not domain types; mapping reconstructs dataclasses so Decimal/UTC validation runs at the persistence boundary.

| Table | Keys / notes |
|---|---|
| `system_settings` | `key` PK, `value`, `updated_at` |
| `strategy_versions` | `id` PK, unique (`name`, `version`), `config_hash`, `created_at` |
| `signals` | `signal_id` PK; `trigger_price NUMERIC`; `metadata_json JSONB` (not column `metadata`, which clashes with SQLAlchemy); no FK to `strategy_versions` so historical name/version strings stay even if versions change |
| `risk_decisions` | `decision_id` PK, FK `signal_id`; money/`pct` columns `NUMERIC`; `reason_codes TEXT[]` |
| `orders` | `order_id` PK; **unique `client_order_id`**; unique nullable `exchange_order_id`; optional FKs to signal/risk; status/side CHECKs |
| `fills` | `fill_id` PK, FK `order_id`; `quantity`/`price`/`fee NUMERIC`; `client_order_id` indexed, not unique (many fills per order) |
| `positions` | `position_id` PK; quantity/prices/PnL `NUMERIC` |
| `portfolio_snapshots` | `snapshot_id` PK plus `PortfolioState` fields |
| `risk_events` | `event_id` PK; optional FKs to signal/decision; `code`, `detail` |
| `backtest_runs` | `run_id` PK; strategy/config/dataset hashes; optional `code_commit_sha` |
| `backtest_metrics` | `metric_id` PK; unique (`run_id`, `name`); `value NUMERIC` |
| `system_events` | `event_id` PK; `category`, `event_type`, `payload JSONB` (reconciliation discrepancies later) |

Migrations: `make backend-migrate` (`alembic upgrade head`) and `make backend-migrate-down`. SQLite is not supported for trading state. Control-plane/worker processes do not auto-migrate on startup in this increment.

Repository APIs and transaction-boundary helpers are the next Phase 1 increment.

## Order state machine

Happy path from `docs/04` original chain:

```text
CREATED
→ RISK_APPROVED
→ SUBMITTING
→ SUBMITTED
→ PARTIALLY_FILLED
→ FILLED
```

Explicit allowed transitions implemented in `ORDER_TRANSITIONS`:

```text
CREATED          → RISK_APPROVED | REJECTED
RISK_APPROVED    → SUBMITTING | CANCELED
SUBMITTING       → SUBMITTED | REJECTED | FAILED
SUBMITTED        → PARTIALLY_FILLED | FILLED | CANCELED | FAILED
PARTIALLY_FILLED → FILLED | CANCELED | FAILED
FILLED, CANCELED, REJECTED, FAILED → (terminal)
```

Notes:

- `CREATED → REJECTED` is the risk-reject path so an order identity can exist for audit without being submitted.
- `RISK_APPROVED → CANCELED` allows cancel/HALT before submission.
- Skipping states (for example `CREATED → SUBMITTED`) is invalid.
- `PARTIALLY_FILLED` requires `0 < filled_quantity < quantity`. `FILLED` requires `filled_quantity == quantity`.

Position:

```text
OPENING → OPEN → CLOSING → CLOSED
```

Skipping `OPEN` or `CLOSING`, or reopening `CLOSED`, is invalid. `CLOSED` quantity must be `0`.

## Historical Market Data

OHLCV حجیم در PostgreSQL منبع اصلی Research نیست. ساختار پیشنهادی:

```text
data/market/
  provider=bybit/
    symbol=BTCUSDT/
      timeframe=4h/
        year=2026/month=08/*.parquet
```

Metadata هر dataset:

- provider
- symbol
- timeframe
- start/end UTC
- downloaded_at
- row_count
- checksum/hash
- schema_version

## Redis

فقط برای:

- latest market snapshot cache
- websocket pub/sub
- worker heartbeat
- short-lived distributed locks

حذف Redis نباید تاریخچه یا order state را از بین ببرد.

## Reconciliation

جدول `reconciliation_events` یا `system_events` discrepancyهای زیر را ثبت کند:

- order در DB ولی نه در exchange
- fill در exchange ولی ناشناخته در DB
- position size mismatch
- balance mismatch beyond tolerance

در Live، وضعیت exchange برای balance/order/position واقعیت خارجی نهایی است؛ DB باید با reconciliation به آن همگام شود.
