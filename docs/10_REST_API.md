# 10 — REST & WebSocket Contract

## REST

### System
- `GET /api/health` — liveness only in Phase 0; does not probe PostgreSQL/Redis yet.
- `GET /api/system/status`
- `PATCH /api/system/mode`
- `POST /api/system/halt`
- `POST /api/system/flatten-all`

#### `GET /api/health`

```json
{
  "status": "ok",
  "service": "control-plane",
  "trading_mode": "PAPER",
  "app_env": "development"
}
```

- `trading_mode` is `PAPER` or `SEMI`. `FULL` is rejected at process startup until Phase 10.
- Response header `X-Request-ID` echoes the incoming request ID or a generated UUID.
- This is a liveness check, not a dependency readiness check.
- The Phase 0 Next.js shell reads this payload via a same-origin `/api/*` BFF (server-only `BACKEND_URL`) and displays `trading_mode`. It does not call `/api/system/status` until that route exists.

### Strategies
- `GET /api/strategies`
- `GET /api/strategies/{id}`
- `POST /api/strategies/{id}/activate` — فقط نسخه از قبل validate شده

### Signals
- `GET /api/signals`
- `POST /api/signals/{id}/approve` — SEMI
- `POST /api/signals/{id}/reject`

### Trading state
- `GET /api/orders`
- `GET /api/positions`
- `GET /api/trades`
- `GET /api/portfolio`

### Backtests
- `POST /api/backtests`
- `GET /api/backtests/{id}`
- `GET /api/backtests/{id}/metrics`

## Idempotency

Mutationهای حساس باید `Idempotency-Key` یا resource-state check داشته باشند؛ approve دوباره نباید order دوم بسازد.

## WebSocket

`/ws/dashboard`

Envelope:

```json
{
  "event": "ORDER_UPDATE",
  "timestamp": "2026-08-27T15:00:00Z",
  "sequence": 1024,
  "data": {}
}
```

Events:

- `SYSTEM_STATUS`
- `WORKER_HEARTBEAT`
- `MARKET_STATUS`
- `SIGNAL_CREATED`
- `RISK_DECISION`
- `ORDER_UPDATE`
- `POSITION_UPDATE`
- `PORTFOLIO_UPDATE`
- `RECONCILIATION_ALERT`
- `BACKTEST_PROGRESS`

پس از reconnect، client باید REST resync انجام دهد.

## Auth

در local dev می‌توان auth ساده داشت؛ برای هر deployment قابل دسترس از شبکه عمومی، authentication و authorization اجباری است. APIهای HALT/FLATTEN/approve نباید public unauthenticated باشند.
