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

Framework-independent dataclasses live in `backend/app/domain/`. They are not SQLAlchemy models. Persistence comes in a later Phase 1 increment.

Financial fields are `Decimal`. Wire/JSON serialization uses decimal **strings** (`decimal_to_text`), never binary floats. Timestamps are timezone-aware UTC. Trading entities use UUID primary identities. `client_order_id` is required on `OrderIntent`, `Order`, and `Fill`; uniqueness is a database constraint, not an in-memory guarantee.

`Signal` has no `position_size`. Final size belongs on `RiskDecision.calculated_size` and then `OrderIntent.quantity`.

`OrderIntent` / `Order` / `Position` use `PositionSide` `LONG` | `SHORT`. Mapping to exchange `BUY`/`SELL` is an Execution concern (Phase 6). Order type (`MARKET`/`LIMIT`) is not modeled yet.

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
