# neuroTrade

Quant/Systematic Trading Platform.

Before changing code, read:

1. `AGENTS.md`
2. `docs/00_INDEX.md`
3. `docs/16_CODING_AGENT_GUIDELINES.md`
4. `docs/15_CURSOR_IMPLEMENTATION_CHECKLIST.md`

`TRADING_MODE=PAPER` is the safe default. `FULL` is rejected at process startup until Phase 10 live readiness exists. No live execution is implemented.

## Canonical commands

Run from the repository root. These are the shared Cursor/Codex toolchain commands.

```text
make backend-install      # pip install -e backend[dev]
make backend-lint         # ruff check + ruff format --check
make backend-typecheck    # mypy app
make backend-test         # pytest
make backend-check        # lint + typecheck + tests
make backend-run          # uvicorn control plane on 127.0.0.1:8000
```

Copy `.env.example` to `.env` for local overrides. Do not commit secrets.

## Current status

Phase 0 (Repository Foundation) is in progress:

- Backend FastAPI control plane and `GET /api/health` exist.
- Frontend, Docker Compose, and CI are not implemented yet.
