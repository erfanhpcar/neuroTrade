# 05 — Dashboard UI

Next.js App Router + Tailwind + shadcn/ui.

## صفحات

```text
/
/markets
/strategies
/strategies/[id]
/signals
/orders
/positions
/trades
/backtests
/backtests/[id]
/risk
/system
```

## Dashboard اصلی

نمایش:

- system mode: PAPER / SEMI / FULL / HALTED
- worker heartbeat و آخرین market snapshot
- equity / realized & unrealized PnL
- open risk و daily loss budget
- open positions / pending orders
- latest strategy signals
- reconciliation warnings

## کنترل‌های عملیاتی

### SEMI approval

Modal باید این موارد را نشان دهد:

- strategy + version
- symbol/side/timeframe
- trigger/entry/stop/exit policy
- calculated size
- estimated risk
- RiskDecision reasons
- signal age

Approve فقط اگر signal هنوز معتبر و state idempotent باشد.

### HALT

دکمه مستقل برای جلوگیری از order جدید. این دکمه به معنی بستن فوری positionها نیست.

### FLATTEN ALL

عملیات destructive و جداگانه با تأیید دو مرحله‌ای. نتیجه cancel/closeها باید از backend گزارش شود.

## Backtest UI

- equity curve
- drawdown curve
- monthly returns
- win rate / expectancy / profit factor
- Sharpe/Sortino در صورت تعریف صحیح sampling
- fees/slippage/funding breakdown
- in-sample vs out-of-sample
- parameter/config version

## WebSocket events

- `SYSTEM_STATUS`
- `MARKET_STATUS`
- `SIGNAL_CREATED`
- `RISK_DECISION`
- `ORDER_UPDATE`
- `POSITION_UPDATE`
- `PORTFOLIO_UPDATE`
- `RECONCILIATION_ALERT`
- `BACKTEST_PROGRESS`

پس از reconnect، UI باید state مهم را با REST مجدداً sync کند و فقط به cache وب‌سوکت اعتماد نکند.

## API secrets

API key/secret هیچ‌وقت در browser localStorage، client bundle یا `NEXT_PUBLIC_*` قرار نمی‌گیرد. مدیریت secret سمت backend/deployment است.
