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

Historical OHLCV/`MarketSnapshot` is not stored in PostgreSQL. Before a later Parquet write, call `require_contiguous_ohlcv` so missing or off-grid bars cannot be persisted silently. `inspect_series` reports gaps without changing `fetch_ohlcv` return values.

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

## Repository layer and transaction boundaries

Trading rows are written through `UnitOfWork` (`backend/app/infrastructure/db/unit_of_work.py`) and repositories (`backend/app/infrastructure/db/repositories.py`). ORM rows remain persistence records; repositories reconstruct `app.domain` dataclasses via the existing mapping functions.

Rules:

- `async with UnitOfWork(session_factory)` opens one PostgreSQL transaction.
- `await uow.commit()` is required to persist. Exiting without commit, or with an exception, rolls back.
- Do not hold a unit of work open across exchange or other network I/O. Persist locally, then talk to the network, then open a new unit of work if needed.
- `orders.client_order_id` uniqueness is exposed as `DuplicateClientOrderId`, not a raw SQLAlchemy `IntegrityError`.
- `OrderRepository.save` / `PositionRepository.save` refuse status skips that `ORDER_TRANSITIONS` / `POSITION_TRANSITIONS` forbid.
- Look up in-flight orders by `get_by_client_order_id` for later idempotency/reconciliation. `OrderIntent` is still not a table.

`system_settings`, `strategy_versions`, `risk_events`, `backtest_*`, and `system_events` are migrated but do not yet have repositories. Those remain later increments when a caller exists.

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

OHLCV حجیم در PostgreSQL منبع اصلی Research نیست. Phase 2 layout:

```text
data/market/
  provider=bybit/
    symbol=BTCUSDT/
      timeframe=4h/
        metadata.json
        year=2026/month=08/ohlcv-v1.parquet
```

`ParquetOhlcvStore` (`backend/app/market_data/parquet.py`) writes this tree. Hive `symbol=` strips non-alphanumeric characters (`BTC/USDT` → `BTCUSDT`). Month partitions are physical layout only; one dataset is the full contiguous series at the timeframe directory.

`metadata.json` fields:

- `schema_version` (`ohlcv-v1`)
- provider, symbol, timeframe
- start/end UTC (`open_time` of first/last bar)
- downloaded_at (injected by the caller; the writer has no wall clock)
- row_count
- `dataset_hash` (same SHA-256 as `hash_ohlcv_bars`; bar contents, not file bytes)
- `files[]`: relative path, row_count, SHA-256 of parquet bytes

Prices and volume are stored as canonical decimal strings, never `float64`. Writes call `require_contiguous_ohlcv` first and refuse empty series. A second write with a different `dataset_hash` is rejected (`ImmutableOhlcvDataset`). An identical hash is idempotent and keeps the original `downloaded_at`. Reads recompute both per-file SHA-256 and `dataset_hash`. Generated files under `backend/data/market/` remain gitignored.

Live ticker/kline WebSocket updates are not stored in Parquet. Unconfirmed klines (`confirm=False`) are in-progress venue OHLC and must not be written as closed historical bars.

Calendar `1M` is still unsupported (ISSUE-0016). Incremental append of extra months onto an existing hash is not implemented; replace only when the full-series hash matches.

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
