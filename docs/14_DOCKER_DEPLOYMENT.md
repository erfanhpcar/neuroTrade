# 14 — Docker Deployment

## سرویس‌های Compose

```text
postgres
redis
backend          # FastAPI control plane
trading-worker   # strategy/risk/execution loop
frontend         # Next.js
```

Backtest worker جدا فقط زمانی اضافه شود که jobهای سنگین API/worker اصلی را مختل کنند.

## شبکه و persistence

- PostgreSQL named volume
- `backend/data/market` برای Parquet در dev؛ production بهتر است volume/object storage policy مشخص داشته باشد
- Redis persistent state محسوب نمی‌شود
- backend و worker از یک image/codebase استفاده می‌کنند ولی command متفاوت دارند

## env نمونه

```env
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://neurotrade:pass@postgres:5432/neurotrade
REDIS_URL=redis://redis:6379/0
TRADING_MODE=PAPER
MARKET_DATA_PROVIDER=bybit
DEFAULT_SYMBOL=BTC/USDT
DEFAULT_TIMEFRAME=4h

# فقط در فاز private execution
EXCHANGE_ID=
EXCHANGE_API_KEY=
EXCHANGE_API_SECRET=
```

Secret واقعی commit نشود.

## startup safety

- default mode = `PAPER`
- startup worker در صورت config ناقص private API نباید به Live fallback کند
- `FULL` از env تصادفی فعال نشود؛ نیازمند persisted explicit state + deployment policy
- قبل از processing، migrations و DB health بررسی شوند

## health

- `/api/health` برای API
- worker heartbeat در DB/Redis
- postgres/redis healthcheck
- UI باید stale worker را واضح نشان دهد

## production

- reverse proxy + TLS
- private DB/Redis ports
- authenticated dashboard
- log rotation/central logging
- backup PostgreSQL
- static server IP برای exchange IP whitelist در صورت پشتیبانی
