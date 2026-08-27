# 11 — Implementation Guide

## Development order

### Phase A — Foundation
- monorepo skeleton
- Docker Compose: postgres, redis, backend, trading-worker, frontend
- config validation
- structured logging
- CI: lint + typecheck + tests
- health endpoints

### Phase B — Market Data
- provider interface
- Bybit/Binance public adapter
- historical OHLCV downloader
- Parquet dataset metadata/hash
- live ticker/candle WebSocket
- gap/missing candle detection

### Phase C — Strategy V1
- domain models
- Strategy protocol
- trend/momentum V1
- deterministic replay tests
- no-look-ahead tests

### Phase D — Backtest
- market simulator
- fees/slippage/funding
- portfolio accounting
- metrics
- OOS + walk-forward runner
- experiment persistence

### Phase E — Risk & Portfolio
- position sizing
- risk limits
- atomic exposure reservation
- HALT state
- tests for race/boundaries

### Phase F — Paper Execution
- PaperExecutionAdapter
- order/position state machines
- fills
- reconciliation loop
- restart recovery

### Phase G — API/UI
- REST + WebSocket
- dashboard
- signals/orders/positions/backtests/risk
- SEMI approval
- HALT + FLATTEN ALL

### Phase H — Testnet / Exchange
- validate selected exchange auth/docs
- private API adapter
- API key permissions minimal
- IP whitelist where available
- tiny-size testnet/demo orders
- timeout/idempotency/reconciliation tests

### Phase I — Live Hardening
- auth/RBAC
- secret rotation
- monitoring/alerts
- DB backup/restore drill
- chaos scenarios: API timeout, WS disconnect, restart during order
- runbook

## Definition of Done MVP

MVP تمام است وقتی:

1. یک dataset نسخه‌بندی‌شده دانلود می‌شود.
2. Strategy V1 بدون look-ahead روی آن replay می‌شود.
3. Backtest با fee/slippage گزارش قابل تکرار می‌دهد.
4. Paper worker همان Strategy را live اجرا می‌کند.
5. Risk limits order نامعتبر را رد می‌کنند.
6. restart باعث duplicate order نمی‌شود.
7. reconciliation discrepancy را تشخیص می‌دهد.
8. dashboard state را نشان می‌دهد و SEMI flow کار می‌کند.
9. هیچ LLM/API هوش مصنوعی برای این مسیر لازم نیست.

مرجع اجرای دقیق Cursor: `15_CURSOR_IMPLEMENTATION_CHECKLIST.md`.
