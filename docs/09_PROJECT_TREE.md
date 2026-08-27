# 09 — Project Tree

```text
neuroTrade/
├── AGENTS.md                     # قواعد مشترک Cursor/Codex
├── .cursor/
│   └── rules/
│       ├── 00-neurotrade-core.mdc
│       ├── backend-python.mdc
│       └── frontend-nextjs.mdc
├── Makefile                      # canonical lint/typecheck/test/compose commands
├── docker-compose.yml            # postgres, redis, backend, trading-worker, frontend
├── docker-compose.override.yml   # local only; gitignored
├── .gitignore
├── .env.example
├── docs/
│   ├── 00_INDEX.md
│   ├── ...
│   ├── 16_CODING_AGENT_GUIDELINES.md
│   └── 17_DEVELOPMENT_ISSUES.md
├── backend/
│   ├── AGENTS.md                 # قواعد scoped بک‌اند
│   ├── app/
│   │   ├── main.py               # FastAPI control plane
│   │   ├── config.py             # TRADING_MODE default PAPER
│   │   ├── domain/               # framework-independent dataclasses
│   │   │   ├── market.py
│   │   │   ├── signal.py
│   │   │   ├── risk.py
│   │   │   ├── order.py
│   │   │   ├── position.py
│   │   │   └── portfolio.py
│   │   ├── strategies/
│   │   │   ├── base.py
│   │   │   └── trend_following/
│   │   ├── market_data/
│   │   │   ├── base.py            # MarketDataProvider + OhlcvSeries
│   │   │   ├── replay.py          # fixture-backed provider; no network
│   │   │   ├── bybit.py           # later public REST/WS adapter
│   │   │   └── binance.py         # later public REST/WS adapter
│   │   ├── risk/
│   │   │   ├── engine.py
│   │   │   ├── sizing.py
│   │   │   └── limits.py
│   │   ├── execution/
│   │   │   ├── base.py
│   │   │   ├── paper.py
│   │   │   ├── ccxt_adapter.py
│   │   │   ├── true_trade.py      # فقط پس از اعتبارسنجی API
│   │   │   └── reconciliation.py
│   │   ├── portfolio/
│   │   │   └── engine.py
│   │   ├── backtest/
│   │   │   ├── engine.py
│   │   │   ├── simulator.py
│   │   │   └── metrics.py
│   │   ├── api/
│   │   │   ├── system.py
│   │   │   ├── strategies.py
│   │   │   ├── signals.py
│   │   │   ├── orders.py
│   │   │   ├── positions.py
│   │   │   └── backtests.py
│   │   ├── infrastructure/
│   │   │   ├── db/                    # ORM rows, mapping, UnitOfWork, repositories
│   │   │   ├── redis/
│   │   │   └── logging/
│   │   └── workers/
│   │       ├── trading_worker.py      # Phase 0 heartbeat stub
│   │       └── market_data_worker.py  # later
│   ├── alembic/                       # PostgreSQL migrations
│   ├── alembic.ini
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── replay/                    # offline OHLCV JSON fixtures
│   ├── data/
│   │   └── market/
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── AGENTS.md                 # قواعد scoped فرانت‌اند
│   ├── src/app/
│   ├── src/components/
│   ├── src/lib/
│   ├── src/types/
│   ├── Dockerfile
│   └── package.json
└── .github/workflows/
    └── ci.yml
```

## قواعد ساختار

- `AGENTS.md` و `.cursor/rules/` بخشی از architecture governance هستند و با Git version می‌شوند.
- `strategies/` به `execution/` import نکند.
- domain models از FastAPI/CCXT مستقل باشند.
- adapterها در boundary قرار بگیرند.
- tests کنار contractها و behaviorهای حیاتی نوشته شوند.
- فایل secret داخل repo ممنوع.
