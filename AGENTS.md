# neuroTrade — Coding Agent Instructions

This file is the canonical repository-level instruction set for coding agents such as Codex and Cursor. Read it before changing code or documentation.

## 1. Mission and source of truth

neuroTrade is a deterministic Quant/Systematic Trading Platform. V0/V1 is not an AI trading bot.

Before a non-trivial change:
1. Read `docs/00_INDEX.md`.
2. Read the documents relevant to the subsystem being changed.
3. Read any nested `AGENTS.md` that applies to the target directory.
4. Inspect the existing implementation before proposing changes.

If code and docs conflict, do not silently choose one. Report the conflict and resolve it deliberately. Architecture, risk, strategy, execution, persistence, and API-contract changes must update the relevant docs in the same change.

## 2. Workflow

- Keep each task/PR focused on one phase or concern.
- For a normal task inside an already-approved phase: give a concise implementation + test plan, then proceed.
- Stop and request approval before introducing a new architecture pattern, external dependency, exchange integration, destructive migration, or changing trading/risk semantics not already approved in docs.
- Do not refactor unrelated code while implementing a feature or fix.
- Prefer the smallest safe change that preserves explicit contracts.
- Never claim success without running the relevant checks or clearly stating what could not be run.
- At completion report: changed files, behavior changed, tests/checks run with exact results, remaining risks, and the next smallest step.

## 3. Non-negotiable trading safety rules

- Default mode is `PAPER`. Code, tests, examples, and local defaults must never default to `FULL`/live trading.
- Strategy code only emits `Signal`; it must not place orders or calculate final executable size.
- Every executable order must pass the deterministic Risk Engine first.
- AI/LLM output must never bypass Strategy, Risk, Execution, or Reconciliation contracts.
- Backtest and live/paper execution must call the same strategy implementation for signal generation.
- A strategy/risk behavior change requires tests and a new/versioned strategy or config identity where applicable.
- Exchange state is authoritative for actual balances, open orders, fills, and positions; local state must be reconciled.
- `create_order`/equivalent is never blindly retried after an ambiguous timeout. Reconcile by `client_order_id`/exchange order state before deciding whether to retry.
- Order creation must be idempotency-aware; `client_order_id` must be unique and persisted.
- `HALT` (stop new exposure) and `FLATTEN_ALL` (cancel/close exposure) are separate operations.
- `FLATTEN_ALL` and other destructive trading actions require explicit confirmation in UI/API workflows.

## 4. Secrets and exchange permissions

- Never commit or print real API keys, secrets, tokens, seed phrases, private keys, or production `.env` contents.
- Never log auth headers/signatures or full private exchange responses when they may contain secrets.
- Example values must be obviously fake.
- Exchange credentials use least privilege. `Withdrawal` is always disabled. `Transfer` remains disabled unless a future approved design explicitly requires it.
- Prefer IP allowlisting for live/private exchange keys when supported.
- Do not reverse-engineer or rely on undocumented private exchange endpoints for live capital. If official docs are missing, stop at the adapter interface and document the blocker.

## 5. Data and numerical correctness

- All timestamps are timezone-aware UTC at system boundaries and persistence.
- Use `Decimal` for money, prices, quantities, fees, balances, order sizing, and persisted financial values.
- Floating point is acceptable inside vectorized research/statistical calculations when appropriate, but convert/validate at trading and persistence boundaries.
- No look-ahead data in strategy/backtest code. A candle/feature may only use information available at that simulated timestamp.
- Historical datasets are immutable/versioned inputs for reproducible backtests; persist dataset/config/code identifiers with results.
- Missing candles, duplicate candles, stale market data, and out-of-order events must be detected rather than silently ignored.

## 6. Architecture boundaries

- Domain/strategy/risk layers must not depend on FastAPI, Next.js, CCXT, or a specific exchange.
- `strategies/` must never import from `execution/`.
- External APIs are accessed through explicit adapters/interfaces.
- PostgreSQL is the transactional source of truth. Redis is cache/pub-sub/coordination only.
- WebSocket events are a realtime delivery mechanism, not the source of truth; clients must be able to resync through REST/DB-backed state.
- Trading worker lifecycle is independent from the FastAPI HTTP process.
- Avoid hidden global mutable state. Make dependencies explicit and injectable.

## 7. Testing and verification

Every behavior change needs the smallest relevant tests. Critical financial logic requires stronger coverage.

Minimum expectations:
- Strategy/features: deterministic replay + no-look-ahead tests.
- Risk: boundary, invalid-input, aggregate-risk, and concurrency/reservation tests.
- Execution: duplicate, timeout, partial-fill, restart, and reconciliation tests.
- Database: migration from empty DB and rollback/recovery checks when applicable.
- API: contract/status-code tests for behavior changes.
- Frontend: typecheck/lint and tests for stateful/dangerous interactions.

Unit tests must not depend on the public internet. External services use fixtures/fakes for CI. Integration tests that require sandbox/testnet must be explicitly marked and opt-in.

Use repository-provided commands/scripts once Phase 0 defines them. Do not invent a second parallel toolchain.

## 8. Code quality

- Prefer explicit, boring, readable code over clever abstractions.
- Keep functions/modules cohesive and small enough to test independently.
- Add abstractions only when they protect a real boundary or remove demonstrated duplication.
- Public/domain types and non-obvious invariants should be documented.
- Errors at external boundaries must include actionable context but no secrets.
- Structured logs should include correlation identifiers such as signal/order/run IDs.
- No broad `except Exception` that swallows errors. Catch expected failures or re-raise with context.
- Do not leave TODOs in safety-critical paths without an issue/explicit blocker documented.

## 9. Git and scope hygiene

- Never commit generated market datasets, secrets, local DB files, node_modules, virtualenvs, or build outputs.
- Do not overwrite or revert unrelated user work.
- Do not merge to `main` or enable live trading unless explicitly requested.
- Prefer small commits with descriptive messages (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`).
- Documentation-only architecture changes should remain reviewable separately from implementation when practical.

## 10. Areas with additional instructions

- `backend/AGENTS.md`: Python/trading-engine rules.
- `frontend/AGENTS.md`: Next.js/TypeScript/dashboard rules.
- `.cursor/rules/*.mdc`: Cursor-specific persistent/scoped rules.
- `docs/16_CODING_AGENT_GUIDELINES.md`: human-readable explanation of this policy and agent workflow.
