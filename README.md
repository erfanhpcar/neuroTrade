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

GitHub Actions (`.github/workflows/ci.yml`) runs `make backend-check` and `make frontend-check` on pull requests and pushes to `main`. Frontend CI uses `npm ci` against the committed lockfile. Default `TRADING_MODE=PAPER`.

Copy `.env.example` to `.env` for backend overrides. Copy `frontend/.env.example` to `frontend/.env.local` if the control plane is not on `http://127.0.0.1:8000`. Do not commit secrets. Do not put secrets in `NEXT_PUBLIC_*`.

## Current status

Phase 0 (Repository Foundation) is in progress:

- Backend FastAPI control plane and `GET /api/health` exist.
- Next.js operator shell displays liveness and trading mode (PAPER by default).
- Compose defines postgres, redis, backend, trading-worker, and frontend with `TRADING_MODE=PAPER`.
- Trading worker is a heartbeat stub (no Strategy/Risk/Execution).
- GitHub Actions CI runs the canonical backend and frontend checks. Phase 0 Definition of Done still requires a green CI run on GitHub plus a healthy Compose stack.
