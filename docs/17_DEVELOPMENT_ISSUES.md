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
