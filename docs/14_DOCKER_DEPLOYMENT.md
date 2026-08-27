# 14 — Docker Deployment

## سرویس‌های Compose

```text
postgres
redis
backend          # FastAPI control plane
trading-worker   # strategy/risk/execution loop
frontend         # Next.js
```

Canonical commands from the repository root:

```text
make compose-config     # validate docker-compose.yml
make compose-up         # docker compose up --build -d
make compose-ps
make compose-down
```

Phase 0 stack notes:

- `backend` and `trading-worker` share `backend/Dockerfile` (same codebase, different command).
- `trading-worker` runs `python -m app.workers.trading_worker` (heartbeat stub). It does not trade.
- `GET /api/health` remains liveness-only. It does not probe Postgres/Redis.
- Frontend `BACKEND_URL` is server-only. The Next.js `/api/*` BFF reads it at request time (no `NEXT_PUBLIC_*`). Compose sets `BACKEND_URL=http://host.docker.internal:8000` plus `extra_hosts: host.docker.internal:host-gateway` so the dashboard can reach the published control-plane port even when bridge ICC is restricted.
- Default `TRADING_MODE` interpolates to `PAPER`. `FULL` is rejected at process startup until Phase 10.
- A local `docker-compose.override.yml` is gitignored for bind mounts; do not commit it.

Backtest worker جدا فقط زمانی اضافه شود که jobهای سنگین API/worker اصلی را مختل کنند.

## شبکه و persistence

- PostgreSQL named volume
- `backend/data/market` برای Parquet در dev؛ production بهتر است volume/object storage policy مشخص داشته باشد
- Redis persistent state محسوب نمی‌شود
- backend و worker از یک image/codebase استفاده می‌کنند ولی command متفاوت دارند

## env نمونه

```env
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://neurotrade:neurotrade_dev_password@postgres:5432/neurotrade
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

- `/api/health` برای API (Phase 0: liveness only; no Postgres/Redis probe)
- worker heartbeat در DB/Redis (Phase 0 stub logs heartbeat only; Redis/DB write comes when `/api/system/status` consumes it)
- postgres/redis healthcheck in Compose
- UI باید stale worker را واضح نشان دهد (Phase 8; dashboard currently shows control-plane liveness)

## production

- reverse proxy + TLS
- private DB/Redis ports
- authenticated dashboard
- log rotation/central logging
- backup PostgreSQL
- static server IP برای exchange IP whitelist در صورت پشتیبانی
