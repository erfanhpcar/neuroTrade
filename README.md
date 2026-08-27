# neuroTrade

Quant/Systematic Trading Platform.

Before changing code, read:

1. `AGENTS.md`
2. `docs/00_INDEX.md`
3. `docs/16_CODING_AGENT_GUIDELINES.md`
4. `docs/15_CURSOR_IMPLEMENTATION_CHECKLIST.md`

`TRADING_MODE=PAPER` is the safe default. `FULL` is rejected at process startup until Phase 10 live readiness exists. No live execution is implemented.

## Canonical commands

Run from the repository root. These are the shared Cursor/Codex toolchain commands. If `PYTHON` points at a virtualenv, pass an absolute path (`PYTHON=$PWD/.venv/bin/python`); backend targets `cd` into `backend/`.

```text
make backend-install      # pip install -e backend[dev]
make backend-lint         # ruff check + ruff format --check
make backend-typecheck    # mypy app
make backend-test         # pytest
make backend-check        # lint + typecheck + tests
make backend-run          # uvicorn control plane on 127.0.0.1:8000
make backend-migrate      # alembic upgrade head (requires PostgreSQL)
make backend-migrate-down # alembic downgrade -1

make frontend-install     # npm install in frontend/
make frontend-lint        # next lint
make frontend-typecheck   # tsc --noEmit
make frontend-test        # vitest run
make frontend-build       # next build
make frontend-check       # lint + typecheck + tests + build
make frontend-run         # next dev on 127.0.0.1:3000

make compose-config       # validate docker-compose.yml
make compose-up           # postgres, redis, backend, trading-worker, frontend
make compose-ps
make compose-down
```

GitHub Actions (`.github/workflows/ci.yml`) runs `make backend-check` and `make frontend-check` on pull requests and pushes to `main`. Backend CI starts PostgreSQL 16 for Alembic integration tests. Frontend CI uses `npm ci` against the committed lockfile. Default `TRADING_MODE=PAPER`.

Copy `.env.example` to `.env` for backend overrides. Copy `frontend/.env.example` to `frontend/.env.local` if the control plane is not on `http://127.0.0.1:8000`. Do not commit secrets. Do not put secrets in `NEXT_PUBLIC_*`.

## Current status

Phase 0 (Repository Foundation) is complete:

- Backend FastAPI control plane and `GET /api/health` exist.
- Next.js operator shell displays liveness and trading mode (PAPER by default).
- Compose defines postgres, redis, backend, trading-worker, and frontend with `TRADING_MODE=PAPER`.
- Trading worker is a heartbeat stub (no Strategy/Risk/Execution).
- GitHub Actions CI runs the canonical backend and frontend checks and is green.

Phase 1 (Domain Models & Database) is complete on this lineage:

- Domain dataclasses remain independent of SQLAlchemy/FastAPI/CCXT.
- Alembic revision `d587f5e75b76` creates the documented PostgreSQL tables.
- `UnitOfWork` + repositories persist signals, risk decisions, orders, fills, positions, and portfolio snapshots.
- Default `TRADING_MODE=PAPER`. Do not enable live trading.

Phase 2 (Market Data) is in progress, not complete:

- `MarketDataProvider` is an async, exchange-agnostic contract (`fetch_ohlcv`, `latest_snapshot`).
- `ReplayMarketDataProvider` loads offline JSON fixtures. Unit tests do not use the network.
- `BybitPublicRestProvider` fetches public klines via official `GET /v5/market/kline` (no API key, no CCXT). Pagination and a configured rate-limit budget are included. Unit tests use `httpx.MockTransport`.
- `inspect_ohlcv` / `inspect_series` detect missing candles and off-grid timestamps. `require_contiguous_ohlcv` is fail-closed for dataset writes. Providers log gaps; they do not raise.
- `ParquetOhlcvStore` writes immutable hive-partitioned Parquet plus `metadata.json` (`dataset_hash` and per-file SHA-256). Unit tests use a temp directory; generated `backend/data/market/**` stays gitignored.
- `BybitPublicWsStream` consumes official public ticker/kline WebSocket topics with reconnect backoff + jitter. Unconfirmed candles are not closed bars. Unit tests inject a fake socket and do not use the public internet.
