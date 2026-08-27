# 15 — Cursor Implementation Checklist

این سند مسیر اجرایی اصلی برای پیاده‌سازی neuroTrade با Cursor است. هر Phase در branch/PR مستقل انجام شود. Cursor باید قبل از کدنویسی سندهای مرتبط همان Phase را بخواند.

## قواعد کار با Cursor

- [ ] قبل از هر Phase، Cursor ابتدا plan و فایل‌های قابل تغییر را اعلام کند.
- [ ] بدون تأیید معماری، dependency جدید اضافه نکند.
- [ ] Strategy را به Exchange/CCXT وابسته نکند.
- [ ] برای منطق مالی از `Decimal` استفاده کند؛ persistence مالی با float ممنوع.
- [ ] هر feature حیاتی همراه test ساخته شود.
- [ ] هیچ secret، API key یا `.env` واقعی commit نشود.
- [ ] migrationها reversible/قابل بررسی باشند.
- [ ] یک PR فقط یک Phase یا یک concern مشخص داشته باشد.

---

## Phase 0 — Repository Foundation

Cursor context: `00_INDEX`, `01_ARCH_OVERVIEW`, `09_PROJECT_TREE`, `14_DOCKER_DEPLOYMENT`.

- [ ] ساخت `backend/`, `frontend/`, `.github/workflows/`.
- [ ] Python project با pyproject و lint/typecheck/test.
- [ ] FastAPI minimal app + `/api/health`.
- [ ] Next.js minimal dashboard.
- [ ] Dockerfile backend/frontend.
- [ ] Compose برای postgres/redis/backend/trading-worker/frontend.
- [ ] `.env.example` و `.gitignore`.
- [ ] structured logging با correlation/request IDs.
- [ ] CI: backend tests/lint/typecheck + frontend lint/typecheck/build.
- [ ] default `TRADING_MODE=PAPER`.

**Done:** `docker compose up` کل stack را بالا بیاورد و CI سبز باشد.

---

## Phase 1 — Domain Models & Database

Context: `04_DATA_SCHEMAS`, `09_PROJECT_TREE`.

- [ ] Domain modelهای MarketSnapshot, Signal, RiskDecision, OrderIntent, Order, Fill, Position, PortfolioState.
- [ ] Enum/state machineها.
- [ ] SQLAlchemy async + migration framework.
- [ ] جداول settings/strategies/signals/risk/orders/fills/positions/portfolio/events/backtests.
- [ ] unique `client_order_id`.
- [ ] repository layer و transaction boundaries.
- [ ] تست Decimal serialization و state transitionهای نامعتبر.

**Done:** migration از DB خالی اجرا و rollback تست شود.

---

## Phase 2 — Market Data

Context: `07_EXTERNAL_SERVICES`, `12_API_COST_RATE_LIMITS`.

- [ ] `MarketDataProvider` interface.
- [ ] یک provider اولیه (Bybit یا Binance public).
- [ ] historical OHLCV downloader با pagination/rate limit.
- [ ] UTC normalization و duplicate removal.
- [ ] missing-candle detector.
- [ ] Parquet writer + dataset metadata/checksum.
- [ ] WebSocket live ticker/candle stream.
- [ ] reconnect با exponential backoff+jitter.
- [ ] replay fixture برای تست بدون اینترنت.

**Done:** BTC/USDT historical dataset قابل تکرار ساخته و live snapshot دریافت شود؛ API key لازم نباشد.

---

## Phase 3 — Strategy Engine V1

Context: `02_STRATEGY_ENGINE`.

- [ ] `Strategy` Protocol.
- [ ] feature functions pure و بدون side effect.
- [ ] V1 trend/momentum + volatility filter با config versioned.
- [ ] `generate_signal()` بدون import از execution.
- [ ] deterministic replay test.
- [ ] no-look-ahead tests.
- [ ] insufficient/missing data behavior.
- [ ] strategy config hash/version.

**Done:** dataset یکسان همیشه Signal sequence یکسان تولید کند.

---

## Phase 4 — Backtest Engine

Context: `06_BACKTESTING`, `13_STRATEGY_GOVERNANCE`.

- [ ] event/candle simulator.
- [ ] استفاده مستقیم از Strategy V1.
- [ ] simulated order/fill.
- [ ] fee model.
- [ ] slippage/spread model.
- [ ] funding model برای perpetual در صورت استفاده.
- [ ] portfolio accounting.
- [ ] max drawdown/expectancy/profit factor/turnover و metrics دیگر.
- [ ] ambiguous candle deterministic policy.
- [ ] persist `backtest_run` + code/config/dataset hashes.
- [ ] OOS runner.
- [ ] walk-forward runner.
- [ ] sensitivity report.

**Done:** یک backtest fully reproducible با report و costs واقعی‌تر تولید شود.

---

## Phase 5 — Portfolio & Risk

Context: `03_RISK_FIREWALL`.

- [ ] equity/exposure/open-risk calculation.
- [ ] position sizing با fee/slippage budget.
- [ ] exchange precision hooks.
- [ ] max risk per trade.
- [ ] max aggregate risk.
- [ ] max positions/exposure.
- [ ] daily realized + unrealized loss lock.
- [ ] atomic risk reservation برای signalهای همزمان.
- [ ] stale signal rejection.
- [ ] HALT state.
- [ ] extensive unit/property/concurrency tests.

**Done:** هیچ Signal بدون `RiskDecision.APPROVED` به execution نرسد.

---

## Phase 6 — Paper Execution & Reconciliation

Context: `01_ARCH_OVERVIEW`, `04_DATA_SCHEMAS`, `07_EXTERNAL_SERVICES`.

- [ ] `ExecutionAdapter` interface.
- [ ] `PaperExecutionAdapter`.
- [ ] order state machine.
- [ ] fill/partial-fill simulation.
- [ ] unique idempotency/client_order_id.
- [ ] position state machine.
- [ ] restart recovery از DB.
- [ ] reconciliation loop.
- [ ] discrepancy events.
- [ ] test timeout/duplicate/restart scenarios.

**Done:** kill/restart worker وسط order flow باعث duplicate trade یا state گم‌شده نشود.

---

## Phase 7 — Trading Worker

- [ ] worker heartbeat.
- [ ] schedule based on timeframe/event.
- [ ] MarketSnapshot → Strategy → Risk → Execution pipeline.
- [ ] distributed lock فقط در نقاط موردنیاز.
- [ ] graceful shutdown.
- [ ] crash recovery.
- [ ] PAPER mode end-to-end.

**Done:** worker چند روز paper بدون manual intervention و بدون state divergence اجرا شود.

---

## Phase 8 — API & Dashboard

Context: `05_DASHBOARD_UI`, `10_REST_API`.

- [ ] REST endpoints.
- [ ] WebSocket envelope + sequence.
- [ ] reconnect/resync.
- [ ] dashboard overview.
- [ ] strategy/signal/orders/positions/trades pages.
- [ ] backtest report UI.
- [ ] risk page.
- [ ] SEMI approval/reject.
- [ ] HALT.
- [ ] FLATTEN ALL با double confirmation.
- [ ] stale worker/reconciliation warning.

**Done:** state UI بعد از refresh/reconnect با DB سازگار بماند.

---

## Phase 9 — Private Exchange / Testnet

Context: `07_EXTERNAL_SERVICES`.

- [ ] انتخاب exchange فقط بعد از مستندات رسمی و sandbox/demo availability.
- [ ] private auth/signature adapter.
- [ ] balance/positions/open orders/fills.
- [ ] create/cancel order.
- [ ] precision/min notional.
- [ ] rate limits.
- [ ] timeout reconciliation قبل از retry.
- [ ] API key با permission حداقلی.
- [ ] Withdrawal خاموش.
- [ ] IP whitelist در صورت امکان.
- [ ] Testnet/Demo فقط؛ live key ممنوع در این Phase.

### The True Trade
- [ ] endpoint/auth docs رسمی جمع‌آوری شود.
- [ ] مشخص شود Demo/API trading پشتیبانی می‌شود یا نه.
- [ ] `Readonly + Futures Trading` فقط در صورت نیاز.
- [ ] `Transfer=false`, `Withdrawal=false`.
- [ ] adapter پشت همان Execution interface.

**Done:** SEMI mode روی test/demo order کوچک end-to-end و reconciliation موفق داشته باشد.

---

## Phase 10 — Live Readiness

- [ ] dashboard auth/RBAC.
- [ ] TLS/reverse proxy.
- [ ] secrets rotation procedure.
- [ ] PostgreSQL backup + restore drill.
- [ ] monitoring/alerts.
- [ ] reconciliation alerting.
- [ ] exchange outage runbook.
- [ ] DB outage runbook.
- [ ] worker restart drill.
- [ ] HALT drill.
- [ ] FLATTEN ALL drill روی demo/testnet.
- [ ] strategy promotion evidence review.
- [ ] initial live risk بسیار محدود.
- [ ] FULL mode همچنان دستی promote شود.

**Done:** قبل از سرمایه واقعی، paper/testnet evidence و operational runbook تأیید شده باشد.

---

## Phase 11 — AI (Optional, Later)

Context: `08_AI_EXTENSION`.

- [ ] AI فقط خارج از execution path.
- [ ] post-mortem/research assistant prototype.
- [ ] baseline بدون AI حفظ شود.
- [ ] A/B OOS/forward evaluation.
- [ ] latency/cost/failure tracking.
- [ ] هیچ تغییر خودکار Risk/Strategy active.

**Done:** فقط در صورت evidence قابل اندازه‌گیری AI به یک feature رسمی تبدیل شود.

---

## Prompt template برای هر Phase در Cursor

```text
Read the referenced neuroTrade docs first. Do not code yet.
1. Summarize the architecture constraints relevant to this phase.
2. Inspect the current repository and identify the exact files to create/change.
3. Produce a small implementation plan and test plan.
4. Explicitly call out any conflict between the repository and docs.
5. Wait for approval before implementation.

After approval, implement only this phase. Do not refactor unrelated areas.
Run lint/typecheck/tests and report exact results, remaining risks, and the next smallest step.
```
