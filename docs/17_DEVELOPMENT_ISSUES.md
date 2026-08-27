# neuroTrade Development Issues

## Active Issues

### ISSUE-0001 — Phase 0 foundation is incomplete
- Status: OPEN
- Severity: MEDIUM
- Area: Infrastructure
- Found in: Phase 0 / repository root
- Description: Backend FastAPI health and a Next.js operator shell exist, but Phase 0 Definition of Done is not satisfied. Missing pieces: backend/frontend Dockerfiles, Compose for postgres/redis/backend/trading-worker/frontend, a trading-worker process, and CI workflows. shadcn/ui is documented for the dashboard but was not added in the Phase 0 shell; operator safety dialogs belong in Phase 8.
- Why it matters: Agents cannot run the documented stack or gated CI until Compose and CI exist. Trading worker is still absent, so there is no process isolation beyond the control-plane app factory.
- Suggested options: Next increment should add Dockerfiles + Compose with default `TRADING_MODE=PAPER`, then CI.
- Recommended next action: Add backend/frontend Dockerfiles and a Compose file for postgres, redis, backend, trading-worker, and frontend. Worker can be a heartbeat stub; do not implement the trading pipeline.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0002 — Python dependencies are not locked
- Status: OPEN
- Severity: LOW
- Area: Infrastructure
- Found in: `backend/pyproject.toml`
- Description: Backend dependencies are ranged in `pyproject.toml` without a lockfile (`uv.lock` or equivalent). Installs can resolve different versions over time.
- Why it matters: Reproducible CI/backtests will later need pinned installs. This is not a trading-logic defect.
- Suggested options: Keep pip/pyproject as the single toolchain and add a lockfile when CI is introduced, rather than adding a second package manager now. Frontend already commits `package-lock.json`.
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
- Recommended next action: Do not add a new runtime dependency for this warning. Revisit when CI lands or if tests start failing.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0005 — Overlapping Phase 0 draft PRs
- Status: OPEN
- Severity: MEDIUM
- Area: Docs
- Found in: GitHub PRs #2 and #3 vs this increment
- Description: Parallel automation runs produced overlapping Phase 0 drafts. PR #3 (`cursor/development-agent-guidelines-76fd`) is the conservative FastAPI health increment this work continues. PR #2 (`cursor/phase0-foundation-scaffold-1e99`) also adds frontend, Compose, CI, a worker stub, and a different `/api/health` body (`dependencies.postgres/redis`, `status: ok|degraded`) that conflicts with the documented Phase 0 liveness contract.
- Why it matters: Merging both blindly would fork the health API and duplicate frontend/infra. The liveness-only health payload is already documented in `docs/10_REST_API.md`.
- Suggested options: Continue this lineage (PR #3 + Next.js shell). Review PR #2 for reusable Compose/CI/worker pieces, but do not adopt its health contract without an explicit docs change. Close or rebase the superseded draft after review.
- Recommended next action: Human review should treat this branch as the current Phase 0 continuation and keep PR #2 as a reference for Docker/CI only.
- Created: 2026-08-27
- Last reviewed: 2026-08-27

### ISSUE-0007 — Transitive PostCSS advisory inside Next.js 15.5.24
- Status: OPEN
- Severity: LOW
- Area: Frontend
- Found in: `frontend/package.json` / `npm audit --omit=dev`
- Description: After pinning `next@15.5.24` (patched for CVE-2025-66478 and later RSC advisories), `npm audit` still reports a high PostCSS advisory on Next's nested `node_modules/next/node_modules/postcss`. The suggested force-fix is Next 16, a major upgrade not approved for this increment.
- Why it matters: This is a nested toolchain/CSS stringify issue, not trading logic. Jumping to Next 16 without review would be an unapproved dependency major bump.
- Suggested options: Stay on Next 15.5.24 for Phase 0. Revisit Next 16 only with an explicit decision when CI exists.
- Recommended next action: Do not `npm audit fix --force`. Re-check when adding CI.
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
