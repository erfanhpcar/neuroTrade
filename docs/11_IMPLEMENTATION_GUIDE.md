# 11 — Implementation Guide

## قبل از هر کد

چه با Cursor و چه با Codex، agent باید به‌ترتیب این منابع را رعایت کند:

1. `AGENTS.md` در ریشه؛
2. nested `AGENTS.md` مسیر هدف (`backend/AGENTS.md` یا `frontend/AGENTS.md`)؛
3. `docs/00_INDEX.md`؛
4. سندهای subsystem مربوط به Phase؛
5. `docs/16_CODING_AGENT_GUIDELINES.md`؛
6. برای Cursor، Ruleهای `.cursor/rules/*.mdc` نیز به صورت persistent/scoped اعمال می‌شوند.

Checklist اجرایی canonical: `15_CURSOR_IMPLEMENTATION_CHECKLIST.md` (با وجود نام تاریخی فایل، برای Cursor و Codex یکسان است).

## اصل توسعه

هر فاز یک خروجی قابل تست می‌سازد. به فاز بعدی نرو تا Definition of Done فاز فعلی پاس نشده باشد.

## فازها

### Phase 0 — Foundation

- monorepo skeleton
- Docker Compose
- FastAPI health
- Next.js shell
- PostgreSQL/Redis
- trading-worker process
- CI
- `.env.example`
- canonical lint/typecheck/test commands (`make backend-check`; see root `Makefile` / `README.md`)

**Done:** Compose healthy + CI green + default PAPER.

### Phase 1 — Domain/Persistence

- domain types
- migrations
- repositories
- state machines
- idempotency fields

**Done:** empty DB migration + rollback/recovery test.

### Phase 2 — Market Data

- provider interface
- public provider
- historical downloader
- Parquet
- WebSocket
- validation/gap detection

**Done:** reproducible BTC dataset + live snapshot.

### Phase 3 — Strategy V1

- Strategy interface
- trend/momentum implementation
- config/version/hash
- deterministic tests

**Done:** same input => same signals; no look-ahead.

### Phase 4 — Backtest

- simulator
- execution costs
- metrics
- OOS/walk-forward
- reproducibility manifest

**Done:** repeatable report with realistic assumptions.

### Phase 5 — Risk/Portfolio

- equity/exposure
- risk reservation
- sizing
- limits/HALT

**Done:** execution unreachable without Risk approval.

### Phase 6 — Paper Execution/Reconciliation

- adapter contract
- paper adapter
- order/fill/position state
- restart recovery
- reconciliation

**Done:** duplicate/timeout/restart tests pass.

### Phase 7 — Worker

- event/schedule loop
- pipeline
- heartbeat
- graceful shutdown/recovery

**Done:** sustained PAPER run without divergence.

### Phase 8 — API/UI

- REST/WS
- dashboard
- SEMI approval
- HALT/FLATTEN

**Done:** UI resyncs after reconnect and source-of-truth remains consistent.

### Phase 9 — Exchange Sandbox/Demo

Only use documented official APIs. Do not use real money.

**Done:** small sandbox/demo SEMI flow + reconciliation.

### Phase 10 — Live Hardening

Security, monitoring, backup, runbooks, drills, strategy promotion evidence.

### Phase 11 — AI Optional

Only research/post-mortem/advisory experiments after deterministic baseline.

## Policy برای تصمیم‌های جدید

اگر حین implementation نیاز به تصمیمی خارج از docs به وجود آمد، agent نباید با حدس خودش تصمیم معماری بگیرد. برای موارد زیر plan/trade-off ارائه و قبل از implementation تصمیم را مطرح کند:

- architecture pattern جدید؛
- dependency مهم جدید؛
- تغییر Strategy/Risk semantics؛
- تغییر Order/Execution semantics؛
- migration مخرب؛
- REST/WebSocket contract breaking change؛
- exchange/data provider جدید یا undocumented behavior.

Task مشخص داخل یک Phase تصویب‌شده می‌تواند پس از plan کوتاه ادامه پیدا کند.

## Definition of Done عمومی

هر feature قبل از Done:

1. relevant tests pass;
2. lint/typecheck pass;
3. migration/API contracts بررسی شده؛
4. docs در صورت تغییر رفتار به‌روز شده؛
5. هیچ secret وارد Git/log نشده؛
6. exact command results گزارش شده؛
7. known risks و کارهای اجرا نشده شفاف اعلام شده‌اند.

## چیزی که نباید انجام دهیم

- پیاده‌سازی همه فازها در یک prompt/PR؛
- live key در development؛
- تغییر Strategy برای بهتر کردن یک backtest خاص بدون OOS؛
- duplicate implementation برای strategy live/backtest؛
- اتصال UI مستقیم به Exchange؛
- retry کور order؛
- استفاده از AI برای دور زدن Risk؛
- اضافه کردن abstractionهای بزرگ بدون نیاز واقعی؛
- اعلام Done بر اساس «looks correct» بدون verification.
