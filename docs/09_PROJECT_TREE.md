# 09 — Project Tree

```text
neuroTrade/
├── docker-compose.yml
├── docker-compose.override.yml
├── .env.example
├── docs/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── domain/
│   │   │   ├── market.py
│   │   │   ├── signal.py
│   │   │   ├── order.py
│   │   │   ├── position.py
│   │   │   └── portfolio.py
│   │   ├── strategies/
│   │   │   ├── base.py
│   │   │   └── trend_following/
│   │   ├── market_data/
│   │   │   ├── base.py
│   │   │   ├── bybit.py
│   │   │   └── binance.py
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
│   │   │   ├── db/
│   │   │   ├── redis/
│   │   │   └── logging/
│   │   └── workers/
│   │       ├── trading_worker.py
│   │       └── market_data_worker.py
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── replay/
│   ├── data/
│   │   └── market/
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
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

- `strategies/` به `execution/` import نکند.
- domain models از FastAPI/CCXT مستقل باشند.
- adapterها در boundary قرار بگیرند.
- tests کنار contractها و behaviorهای حیاتی نوشته شوند.
- فایل secret داخل repo ممنوع.
