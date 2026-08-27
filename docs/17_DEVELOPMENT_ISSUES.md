# neuroTrade Development Issues

## Active Issues

### ISSUE-0001 — Phase 0 foundation is incomplete
- Status: OPEN
- Severity: MEDIUM
- Area: Infrastructure
- Found in: Phase 0 / repository root
- Description: The backend FastAPI skeleton and `GET /api/health` exist, but Phase 0 Definition of Done is not satisfied. Missing pieces: Next.js dashboard shell, backend/frontend Dockerfiles, Compose for postgres/redis/backend/trading-worker/frontend, and CI workflows.
- Why it matters: Agents cannot run the documented stack or gated CI until these exist. Trading worker is still absent, so there is no process isolation beyond the control-plane app factory.
- Suggested options: Implement the remaining Phase 0 items one concern at a time, starting with the Next.js shell or Compose/Dockerfiles.
- Recommended next action: Add a minimal Next.js dashboard that displays health/trading mode, or add Dockerfiles + Compose with default `TRADING_MODE=PAPER`.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0002 — Python dependencies are not locked
- Status: OPEN
- Severity: LOW
- Area: Infrastructure
- Found in: `backend/pyproject.toml`
- Description: Backend dependencies are ranged in `pyproject.toml` without a lockfile (`uv.lock` or equivalent). Installs can resolve different versions over time.
- Why it matters: Reproducible CI/backtests will later need pinned installs. This is not a trading-logic defect.
- Suggested options: Keep pip/pyproject as the single toolchain and add a lockfile when CI is introduced, rather than adding a second package manager now.
- Recommended next action: Revisit when GitHub Actions is added in Phase 0.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0004 — Starlette TestClient warns that `httpx` is deprecated in favor of `httpx2`
- Status: OPEN
- Severity: LOW
- Area: Testing
- Found in: `make backend-check` / FastAPI 0.141.1 TestClient
- Description: Pytest emits `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` Tests still pass.
- Why it matters: Future Starlette versions may require a new HTTP test client. Adding `httpx2` now would be a new dependency without an approved need.
- Suggested options: Keep `httpx` until CI exists and Starlette requires the change; then add `httpx2` as a dev extra only.
- Recommended next action: Do not add a new dependency in this run. Revisit when frontend/CI work lands or if tests start failing.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

## Resolved Issues

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
