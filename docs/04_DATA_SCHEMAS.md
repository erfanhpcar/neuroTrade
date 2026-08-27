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

## Order state machine

```text
CREATED
→ RISK_APPROVED
→ SUBMITTING
→ SUBMITTED
→ PARTIALLY_FILLED
→ FILLED
→ CANCELED | REJECTED | FAILED
```

Position:

```text
OPENING → OPEN → CLOSING → CLOSED
```

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
