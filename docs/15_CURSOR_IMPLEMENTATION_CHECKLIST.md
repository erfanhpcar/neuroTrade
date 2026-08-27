# 15 — Implementation Checklist (Cursor / Codex)

> نام فایل به دلیل تاریخچه پروژه حفظ شده، اما این checklist برای **هر دو Cursor و Codex** مرجع رسمی پیاده‌سازی است.

این سند مسیر اجرایی اصلی neuroTrade است. هر Phase ترجیحاً در branch/PR مستقل انجام شود. Agent قبل از کدنویسی باید `AGENTS.md`، `docs/00_INDEX.md`، `docs/16_CODING_AGENT_GUIDELINES.md` و سندهای مرتبط همان Phase را بخواند.

## قواعد کار با Coding Agent

- [ ] `AGENTS.md` و nested `AGENTS.md`های مسیر هدف خوانده شوند.
- [ ] قبل از هر Phase، agent فایل‌های موجود، plan و test plan را مشخص کند.
- [ ] اگر تصمیم جدید معماری/Strategy/Risk/Execution/Schema/API/Dependency/Exchange لازم است و قبلاً در docs تصویب نشده، قبل از implementation متوقف شود و تصمیم را مطرح کند.
- [ ] بدون تصمیم معماری تأییدشده dependency مهم جدید اضافه نشود.
- [ ] Strategy به Exchange/CCXT/Execution وابسته نشود.
- [ ] برای منطق مالی executable/persisted از `Decimal` استفاده شود؛ float فقط در research/vectorized math و پشت boundary معتبر.
- [ ] هر feature حیاتی همراه test ساخته شود.
- [ ] هیچ secret، API key یا `.env` واقعی commit/log نشود.
- [ ] migrationها reviewable و rollback/recovery آن‌ها بررسی شود.
- [ ] یک PR فقط یک Phase یا concern مشخص داشته باشد.
- [ ] agent بدون اجرای checks مرتبط task را Done اعلام نکند.
- [ ] در پایان changed files، exact checks/results، known risks و next smallest step گزارش شوند.

---

## Phase 0 — Repository Foundation

Context: `AGENTS.md`, `00_INDEX`, `01_ARCH_OVERVIEW`, `09_PROJECT_TREE`, `14_DOCKER_DEPLOYMENT`, `16_CODING_AGENT_GUIDELINES`.

- [x] ساخت/تکمیل `backend/`, `frontend/`, `.github/workflows/` با حفظ `AGENTS.md`های scoped.
- [x] Python project با `pyproject.toml` و lint/typecheck/test.
- [x] FastAPI minimal app + `/api/health`.
- [x] Next.js minimal dashboard.
- [x] Dockerfile backend/frontend.
- [x] Compose برای postgres/redis/backend/trading-worker/frontend.
- [x] `.env.example` و `.gitignore`.
- [x] structured logging با correlation/request IDs.
- [x] CI: backend tests/lint/typecheck + frontend lint/typecheck/build. *(`make backend-check` + `make frontend-check` via `.github/workflows/ci.yml`; GitHub run 33101838301 green)*
- [x] commandهای canonical پروژه برای checkها مستند شوند تا Cursor/Codex یک toolchain مشترک اجرا کنند.
- [x] default `TRADING_MODE=PAPER`.

**Done:** Compose stack and GitHub Actions CI are verified. Phase 0 is complete. Remaining follow-ups (Python lockfile, Redis heartbeat consumer, Next 16) are tracked in `docs/17_DEVELOPMENT_ISSUES.md` and are not Phase 0 blockers.

---

## Phase 1 — Domain Models & Database

Context: `04_DATA_SCHEMAS`, `09_PROJECT_TREE`, `backend/AGENTS.md`.

- [x] Domain modelهای MarketSnapshot, Signal, RiskDecision, OrderIntent, Order, Fill, Position, PortfolioState. *(in-memory dataclasses in `backend/app/domain/`; no FastAPI/SQLAlchemy/CCXT imports)*
- [x] Enum/state machineها. *(explicit `ORDER_TRANSITIONS` / `POSITION_TRANSITIONS`; invalid transitions raise `InvalidStateTransition`)*
- [x] SQLAlchemy async + migration framework. *(SQLAlchemy 2 async + Alembic; `make backend-migrate`)*
- [x] جداول settings/strategies/signals/risk/orders/fills/positions/portfolio/events/backtests. *(revision `d587f5e75b76`; SQLite not supported)*
- [x] unique `client_order_id`. *(`uq_orders_client_order_id` on `orders`; fills share the parent id and are not unique)*
- [x] repository layer و transaction boundaries. *(`UnitOfWork` + repositories for signals/risk/orders/fills/positions/portfolio; explicit commit, rollback on exception or missing commit; `DuplicateClientOrderId`)*
- [x] تست Decimal serialization و state transitionهای نامعتبر. *(in-memory plus PostgreSQL NUMERIC round-trip)*

**Done:** empty-DB upgrade, unique `client_order_id`, NUMERIC round-trip, downgrade+upgrade recovery, and repository/unit-of-work tests (commit, rollback, duplicate `client_order_id`, invalid order-status skip) are verified. Phase 1 Definition of Done is satisfied.

---

## Phase 2 — Market Data

Context: `07_EXTERNAL_SERVICES`, `12_API_COST_RATE_LIMITS`, `backend/AGENTS.md`.

- [x] `MarketDataProvider` interface. *(`backend/app/market_data/base.py`; `fetch_ohlcv` + `latest_snapshot`)*
- [x] یک provider اولیه (Bybit یا Binance public). *(`BybitPublicRestProvider`; official `GET /v5/market/kline`; no API key; default category `spot`)*
- [x] historical OHLCV downloader با pagination/rate limit. *(`fetch_ohlcv` paginates backward, max 1000/page; configurable `RateLimitBudget`; unit tests use `httpx.MockTransport`)*
- [x] UTC normalization و duplicate removal. *(replay + Bybit adapter both use `normalize_bars`; conflicting duplicates raise)*
- [x] missing-candle/out-of-order detector. *(`inspect_ohlcv` / `inspect_series`; missing grid times, off-grid timestamps, epoch misalignment; `require_contiguous_ohlcv` fail-closed; Bybit logs issues and still returns the series)*
- [x] Parquet writer + dataset metadata/checksum. *(`ParquetOhlcvStore`; hive layout + `metadata.json`; `require_contiguous_ohlcv` before write; `dataset_hash` + per-file SHA-256; prices as canonical decimal strings; pyarrow runtime dependency)*
- [ ] WebSocket live ticker/candle stream.
- [ ] reconnect با exponential backoff+jitter.
- [x] replay fixture برای تست بدون اینترنت. *(`ReplayMarketDataProvider` + `backend/tests/replay/btc_usdt_4h.json`; unit tests perform no network I/O)*

**Done:** BTC/USDT historical dataset قابل تکرار ساخته و live snapshot دریافت شود؛ API key لازم نباشد. Phase 2 is **not** complete until a live WebSocket snapshot path exists. Parquet persistence is implemented; generated datasets stay gitignored.

---

## Phase 3 — Strategy Engine V1

Context: `02_STRATEGY_ENGINE`, `13_STRATEGY_GOVERNANCE`, `backend/AGENTS.md`.

- [ ] `Strategy` Protocol.
- [ ] feature functions pure و بدون side effect.
- [ ] V1 trend/momentum + volatility filter با config versioned.
- [ ] `generate_signal()` بدون import از execution، DB، network یا clock پنهان.
- [ ] deterministic replay test.
- [ ] no-look-ahead tests.
- [ ] insufficient/missing data behavior.
- [ ] strategy config hash/version.

**Done:** dataset/config یکسان همیشه Signal sequence یکسان تولید کند و همان implementation قابل استفاده در Backtest/Live باشد.

---

## Phase 4 — Backtest Engine

Context: `06_BACKTESTING`, `13_STRATEGY_GOVERNANCE`.

- [ ] event/candle simulator.
- [ ] استفاده مستقیم از Strategy V1، بدون strategy implementation دوم برای backtest.
- [ ] simulated order/fill.
- [ ] fee model.
- [ ] slippage/spread model.
- [ ] funding model برای perpetual در صورت استفاده.
- [ ] portfolio accounting.
- [ ] max drawdown/expectancy/profit factor/turnover و metrics دیگر.
- [ ] ambiguous candle deterministic/pessimistic policy.
- [ ] persist `backtest_run` + code/config/dataset hashes.
- [ ] OOS runner.
- [ ] walk-forward runner.
- [ ] sensitivity report.

**Done:** backtest fully reproducible با report و costs واقعی‌تر تولید شود و no-look-ahead regression tests سبز باشند.

---

## Phase 5 — Portfolio & Risk

Context: `03_RISK_FIREWALL`, `backend/AGENTS.md`.

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
- [ ] extensive unit/boundary/concurrency tests.

**Done:** هیچ Signal بدون `RiskDecision.APPROVED` به execution نرسد و concurrent approvals نتوانند limitها را دور بزنند.

---

## Phase 6 — Paper Execution & Reconciliation

Context: `01_ARCH_OVERVIEW`, `04_DATA_SCHEMAS`, `07_EXTERNAL_SERVICES`, `backend/AGENTS.md`.

- [ ] `ExecutionAdapter` interface.
- [ ] `PaperExecutionAdapter`.
- [ ] order state machine.
- [ ] fill/partial-fill simulation.
- [ ] unique/persisted idempotency `client_order_id`.
- [ ] position state machine.
- [ ] restart recovery از DB.
- [ ] reconciliation loop.
- [ ] discrepancy events.
- [ ] timeout test: ambiguous submission قبل از retry حتماً reconcile شود.
- [ ] duplicate/restart/partial-fill scenarios.

**Done:** kill/restart worker وسط order flow باعث duplicate trade یا state گم‌شده نشود.

---

## Phase 7 — Trading Worker

Context: `01_ARCH_OVERVIEW`, `03_RISK_FIREWALL`, `backend/AGENTS.md`.

- [ ] worker heartbeat.
- [ ] schedule based on timeframe/event.
- [ ] MarketSnapshot → Strategy → Risk → Execution pipeline.
- [ ] distributed lock فقط در نقاط موردنیاز.
- [ ] graceful shutdown.
- [ ] crash recovery.
- [ ] PAPER mode end-to-end.
- [ ] worker مستقل از lifecycle پروسه HTTP FastAPI.

**Done:** worker چند روز paper بدون manual intervention، duplicate order یا state divergence اجرا شود.

---

## Phase 8 — API & Dashboard

Context: `05_DASHBOARD_UI`, `10_REST_API`, `frontend/AGENTS.md`.

- [ ] REST endpoints.
- [ ] WebSocket envelope + sequence.
- [ ] reconnect/resync از REST در sequence gap.
- [ ] dashboard overview.
- [ ] strategy/signal/orders/positions/trades pages.
- [ ] backtest report UI.
- [ ] risk page.
- [ ] SEMI approval/reject.
- [ ] HALT.
- [ ] FLATTEN ALL با double confirmation.
- [ ] stale worker/reconciliation warning.
- [ ] هیچ private secret در browser bundle یا `NEXT_PUBLIC_*`.

**Done:** state UI بعد از refresh/reconnect با source of truth سازگار بماند و safety actions رفتار روشن و قابل تست داشته باشند.

---

## Phase 9 — Private Exchange / Testnet

Context: `07_EXTERNAL_SERVICES`, `03_RISK_FIREWALL`.

- [ ] انتخاب exchange فقط بعد از مستندات رسمی و sandbox/demo availability.
- [ ] private auth/signature adapter.
- [ ] balance/positions/open orders/fills.
- [ ] create/cancel order.
- [ ] precision/min notional.
- [ ] rate limits.
- [ ] timeout reconciliation قبل از retry.
- [ ] API key با permission حداقلی.
- [ ] Withdrawal خاموش.
- [ ] Transfer خاموش مگر design آینده صریحاً آن را تصویب کند.
- [ ] IP whitelist در صورت امکان.
- [ ] Testnet/Demo فقط؛ live key ممنوع در این Phase.

### The True Trade
- [ ] endpoint/auth/signature/rate-limit docs رسمی جمع‌آوری شود.
- [ ] مشخص شود Demo/API trading پشتیبانی می‌شود یا نه.
- [ ] `Readonly + Futures Trading` فقط در صورت نیاز.
- [ ] `Transfer=false`, `Withdrawal=false`.
- [ ] اگر API رسمی لازم برای execution وجود ندارد، agent endpoint خصوصی undocumented را برای live reverse-engineer نکند؛ adapter blocked باقی بماند.
- [ ] adapter پشت همان `ExecutionAdapter` interface.

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
- [ ] initial live risk بسیار محدود و explicit.
- [ ] FULL mode فقط با promotion دستی.

**Done:** قبل از سرمایه واقعی، paper/testnet evidence، operational runbooks و risk approval مرور شده باشند.

---

## Phase 11 — AI (Optional, Later)

Context: `08_AI_EXTENSION`.

- [ ] AI فقط خارج از execution-critical path.
- [ ] post-mortem/research assistant prototype.
- [ ] baseline بدون AI حفظ شود.
- [ ] A/B OOS/forward evaluation.
- [ ] latency/cost/failure tracking.
- [ ] هیچ تغییر خودکار Risk/Strategy active.

**Done:** فقط در صورت evidence قابل اندازه‌گیری AI به feature رسمی تبدیل شود.

---

## Prompt استاندارد برای شروع هر Phase در Cursor یا Codex

```text
Read AGENTS.md, docs/00_INDEX.md, docs/16_CODING_AGENT_GUIDELINES.md,
and the documents referenced for this phase before editing anything.

Inspect the current repository and provide:
1. the architecture constraints relevant to this phase,
2. the exact files you expect to create/change,
3. a small implementation plan,
4. a test/verification plan,
5. any conflict or missing decision in the docs.

If the task requires a new architectural, strategy, risk, execution, schema,
API, dependency, or exchange decision that is not already approved, stop and ask before implementing it.

Otherwise implement only the requested phase/concern. Do not refactor unrelated code.
After implementation run the repository-defined checks and report exact results,
changed files, remaining risks, and the next smallest step.
```
