# neuroTrade Development Issues

## Active Issues

### ISSUE-0014 — Bar availability at open vs close is underspecified
- Status: NEEDS_DECISION
- Severity: HIGH
- Area: Data
- Found in: `backend/app/domain/market.py` / `backend/app/market_data/base.py`
- Description: `MarketSnapshot` forbids `bar.open_time > timestamp` but allows `open_time == timestamp`. `MarketDataProvider.latest_snapshot` therefore returns the last bar with `open_time <= timestamp`. For a 4h candle, OHLC at `open_time` is not known until the bar closes (`open_time + timeframe`). Using that bar at decision time `open_time` would be look-ahead.
- Why it matters: Strategy and backtest correctness depend on when a candle is considered closed. Guessing a close-only rule now would change domain semantics without approval.
- Suggested options: Keep the current guard until Phase 3/4; or require `open_time + timeframe <= timestamp` before a bar is eligible (stricter no-look-ahead).
- Recommended next action: Human confirm bar-close availability before Strategy V1 / Backtest consume `latest_snapshot`. Do not change `MarketSnapshot` in this increment.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0013 — Processes do not auto-run migrations on startup
- Status: OPEN
- Severity: LOW
- Area: Infrastructure
- Found in: `docs/14_DOCKER_DEPLOYMENT.md` / FastAPI and trading-worker entrypoints
- Description: `docs/14` says migrations should be checked before processing. `make backend-migrate` and CI Postgres exist, and repositories now read/write trading tables, but neither the control plane nor the worker runs Alembic at process start.
- Why it matters: A freshly composed API could boot against an empty schema. Auto-migrate-on-start is an operational choice (expand/migrate job vs in-process).
- Suggested options: Keep explicit `alembic upgrade` for now; add a Compose/CI migrate step or a dedicated migrate command before worker start.
- Recommended next action: Do not auto-migrate inside the HTTP process. Decide a startup migrate path when the worker actually reads trading tables.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0010 — Order terminal transitions were underspecified
- Status: OPEN
- Severity: MEDIUM
- Area: Execution
- Found in: `docs/04_DATA_SCHEMAS.md` / `backend/app/domain/order.py`
- Description: The original order diagram listed `CANCELED | REJECTED | FAILED` without saying which non-terminal states may enter them. Phase 1 implements an explicit `ORDER_TRANSITIONS` table, including `CREATED → REJECTED` (risk reject before submit) and `RISK_APPROVED → CANCELED` (cancel/HALT before submit). Happy-path skipping remains forbidden.
- Why it matters: Wrong edges would later allow duplicate submission or block HALT-cancel of an unsent order.
- Suggested options: Keep the implemented table; tighten or extend it only with a documented execution-semantics change.
- Recommended next action: Human confirm the table in `docs/04_DATA_SCHEMAS.md` before Phase 6 paper execution uses it.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0011 — Exchange BUY/SELL and order type are not on domain Order
- Status: OPEN
- Severity: LOW
- Area: Execution
- Found in: `backend/app/domain/order.py`
- Description: Domain `Order`/`OrderIntent` use `PositionSide` LONG/SHORT and do not include `MARKET`/`LIMIT`. Docs do not specify those execution fields yet.
- Why it matters: Private/paper adapters will need an exchange side and order type. Inventing them now would be an unapproved execution-semantic decision.
- Suggested options: Add exchange side/type at the Execution adapter boundary in Phase 6, keeping domain direction as LONG/SHORT.
- Recommended next action: Leave unset until `ExecutionAdapter` is specified in Phase 6.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0002 — Python dependencies are not locked
- Status: OPEN
- Severity: LOW
- Area: Infrastructure
- Found in: `backend/pyproject.toml`
- Description: Backend dependencies remain ranged in `pyproject.toml`. CI installs with `pip install -e backend[dev]` and caches from that file. No `uv.lock` / pip-tools lockfile was added, because that would introduce a second package manager or a new pinning workflow not yet approved. Frontend CI uses `npm ci` against `package-lock.json`.
- Why it matters: Reproducible CI/backtests will later need pinned Python installs. This is not a trading-logic defect.
- Suggested options: Keep pip/pyproject as the single backend toolchain. Add a dedicated lockfile later without switching to uv unless a human approves that package manager.
- Recommended next action: Leave unpinned until a human chooses pip-tools vs uv. Do not block Phase 1 on this.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0004 — Starlette TestClient warns that `httpx` is deprecated in favor of `httpx2`
- Status: OPEN
- Severity: LOW
- Area: Testing
- Found in: `make backend-check` / FastAPI 0.141.1 TestClient
- Description: Pytest emits `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` Tests still pass.
- Why it matters: Future Starlette versions may require a new HTTP test client. Adding `httpx2` now would be a new dependency without an approved need.
- Suggested options: Keep `httpx` until Starlette requires the change; then add `httpx2` as a dev extra only.
- Recommended next action: Do not add a new runtime dependency for this warning. Revisit if CI tests start failing.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0005 — Overlapping Phase 0 draft PRs
- Status: OPEN
- Severity: MEDIUM
- Area: Docs
- Found in: GitHub PRs #2, #3, #4, #5, #6
- Description: Parallel automation runs produced overlapping Phase 0 drafts. Current implementation lineage is PR #9 (`cursor/development-agent-guidelines-ee5e`, Phase 1 repositories stacked on PR #8) plus this Phase 2 market-data interface increment. PR #2 (`cursor/phase0-foundation-scaffold-1e99`) was used only as a CI workflow-shape reference; its `/api/health` body (`dependencies.postgres/redis`, `status: ok|degraded`) still conflicts with the documented liveness contract and was not adopted.
- Why it matters: Merging PR #2 blindly would fork the health API.
- Suggested options: Continue this lineage. Close or rebase superseded drafts after human review.
- Recommended next action: Human review should treat PR #9 as current Phase 1 tip. This increment stacks on PR #9. Close or rebase superseded drafts #2/#3/#4/#5 after review.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0007 — Transitive PostCSS advisory inside Next.js 15.5.24
- Status: OPEN
- Severity: LOW
- Area: Frontend
- Found in: `frontend/package.json` / `npm audit --omit=dev`
- Description: After pinning `next@15.5.24` (patched for CVE-2025-66478 and later RSC advisories), `npm audit` still reports a high PostCSS advisory on Next's nested `node_modules/next/node_modules/postcss`. The suggested force-fix is Next 16, a major upgrade not approved for this increment.
- Why it matters: This is a nested toolchain/CSS stringify issue, not trading logic. Jumping to Next 16 without review would be an unapproved dependency major bump.
- Suggested options: Stay on Next 15.5.24 for Phase 0. Revisit Next 16 only with an explicit decision.
- Recommended next action: Do not `npm audit fix --force`. Re-check audit output when frontend dependencies change.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0008 — Worker heartbeat is log-only
- Status: OPEN
- Severity: LOW
- Area: Infrastructure
- Found in: `backend/app/workers/trading_worker.py` / `docs/14_DOCKER_DEPLOYMENT.md`
- Description: `docs/14` says worker heartbeat lives in DB/Redis. Phase 0 implements a process-isolated heartbeat stub that emits structured logs only. No Redis client was added, so Redis remains unused infrastructure until a consumer exists.
- Why it matters: The dashboard cannot yet detect a stale worker. Adding `redis` now would be a new runtime dependency without an API/UI reader, and unit tests would need a fake Redis.
- Suggested options: Keep log-only heartbeat until `/api/system/status` (or an equivalent readiness field) is specified to read it. Then persist heartbeat to Redis with TTL as cache/coordination, not as trading source of truth.
- Recommended next action: Keep log-only heartbeat for now. Wire Redis/DB heartbeat when `/api/system/status` is specified in Phase 8 or when a worker-staleness consumer exists.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

## Resolved Issues

### ISSUE-0012 — Repository layer is not started
- Status: RESOLVED
- Severity: LOW
- Area: Database
- Found in: Phase 1 persistence increment / `backend/app/infrastructure/db/`
- Description: Added `UnitOfWork` and repositories for signals, risk decisions, orders, fills, positions, and portfolio snapshots. Reuses existing ORM rows and mapping functions. Commit is explicit; missing commit or exceptions roll back. Duplicate `client_order_id` is `DuplicateClientOrderId`.
- Why it matters: Callers no longer need to scatter session/commit logic for the trading tables.
- Suggested options: n/a
- Recommended next action: Phase 2 `MarketDataProvider` + replay fixture exist on this lineage. Next smallest task is a public Bybit or Binance REST OHLCV adapter with pagination/rate limits. Do not add a second domain model layer.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0001 — Phase 0 foundation is incomplete
- Status: RESOLVED
- Severity: MEDIUM
- Area: Infrastructure
- Found in: Phase 0 / repository root
- Description: FastAPI health, Next.js operator shell, trading-worker heartbeat stub, Dockerfiles, Compose, and `.github/workflows/ci.yml` exist. Compose was verified with `docker compose up` on the prior increment. GitHub Actions run 33101838301 is green (`backend-check` 25s, `frontend-check` 42s).
- Why it matters: Phase 0 Definition of Done required Compose plus gated CI.
- Suggested options: n/a
- Recommended next action: Phase 1 persistence and repository layer exist. Close or rebase superseded drafts #2/#3/#4/#5 after review.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0009 — Frontend rewrite destination is baked at image build
- Status: RESOLVED
- Severity: LOW
- Area: Frontend
- Found in: `frontend/next.config.ts` / `frontend/Dockerfile`
- Description: Next.js `rewrites()` baked `BACKEND_URL` at build time. Replaced with a same-origin `/api/[...path]` BFF that reads `BACKEND_URL` at request time. Compose uses `host.docker.internal:host-gateway` because this environment's user-defined bridge did not allow container-to-container TCP to `backend:8000`.
- Why it matters: The operator dashboard must reach the control plane without `NEXT_PUBLIC_*` URLs.
- Suggested options: n/a
- Recommended next action: If a later environment has working ICC, `BACKEND_URL=http://backend:8000` remains valid at runtime without a frontend rebuild.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0006 — Next.js 15.1.6 is affected by CVE-2025-66478
- Status: RESOLVED
- Severity: HIGH
- Area: Frontend
- Found in: `frontend/package.json` during Phase 0 dashboard bootstrap
- Description: npm warned that Next.js 15.1.6 is affected by critical RSC issues (CVE-2025-66478 and later DoS/source-exposure advisories). The dashboard pins `next@15.5.24`, `eslint-config-next@15.5.24`, `react@19.0.1`, and `react-dom@19.0.1` rather than the unpatched 15.1.6 line.
- Why it matters: An unauthenticated RCE or DoS in the operator UI would be a control-plane compromise even before live trading exists.
- Suggested options: n/a
- Recommended next action: Re-check `npm audit` when CI is added. Keep Next.js on a patched 15.x release; do not revert to 15.1.0–15.1.8.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0003 — Health endpoint payload was unspecified
- Status: RESOLVED
- Severity: LOW
- Area: API
- Found in: `docs/10_REST_API.md`
- Description: `GET /api/health` was listed without a response body. Phase 0 implemented a liveness payload and documented it.
- Why it matters: Control-plane clients and tests need a stable contract.
- Suggested options: n/a
- Recommended next action: Keep later readiness checks (`postgres`/`redis`/worker heartbeat) as a separate endpoint or an additive field after Compose exists.
- Created: 2026-08-27
- Last reviewed: 2026-08-27
