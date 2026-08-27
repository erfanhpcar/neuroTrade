# ۱۴ — استقرار با Docker (روش رسمی اجرا)

**کل سیستم neuroTrade با Docker بالا می‌آید** — توسعه، تست Testnet و استقرار محلی/سرور همگی بر پایه `docker compose` هستند. نصب دستی Python/Node روی میزبان فقط برای دیباگ اختیاری است، نه مسیر رسمی.

## سرویس‌ها

| سرویس | تصویر / ساخت | پورت (host) | نقش |
|--------|----------------|-------------|-----|
| `postgres` | `postgres:16-alpine` | `5432` | دیتابیس — `04_DATA_SCHEMAS` |
| `redis` | `redis:7-alpine` | `6379` | Pub/Sub WebSocket |
| `backend` | `Dockerfile` در `backend/` | `8000` | FastAPI + LangGraph + Zone Gate |
| `frontend` | `Dockerfile` در `frontend/` | `3000` | Next.js داشبورد |
| `scheduler` *(اختیاری)* | همان image بک‌اند | — | Cron ممیزی هفتگی — `13` |

همه سرویس‌ها در شبکهٔ داخلی `neurotrade-net`؛ بک‌اند به DB/Redis با **hostname سرویس** (`postgres`, `redis`) وصل می‌شود — نه `localhost`.

## ساختار فایل‌ها (ریشه پروژه)

```
neuroTrade/
├── docker-compose.yml
├── docker-compose.override.yml   # اختیاری — dev (reload)
├── .env.example                  # الگو؛ کپی به .env (در .gitignore)
├── backend/
│   └── Dockerfile
└── frontend/
    └── Dockerfile
```

## `docker-compose.yml` (قرارداد)

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: neurotrade
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: neurotrade
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U neurotrade"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  backend:
    build: ./backend
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://neurotrade:${POSTGRES_PASSWORD}@postgres:5432/neurotrade
      REDIS_URL: redis://redis:6379/0
    ports:
      - "8000:8000"
    volumes:
      - ./backend/data:/app/data
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
      NEXT_PUBLIC_WS_URL: ws://localhost:8000/ws/dashboard
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  pgdata:
```

> در production روی سرور، `NEXT_PUBLIC_*` را با دامنه/پروکسی واقعی (Nginx/Caddy) تنظیم کنید.

## راه‌اندازی (مسیر رسمی)

```bash
# ۱. کلیدها
cp .env.example .env
# ویرایش: POSTGRES_PASSWORD, OPENROUTER_API_KEY, EXCHANGE_*, CRYPTOPANIC_TOKEN

# ۲. بالا آوردن کل استک
docker compose up -d --build

# ۳. migration / جداول (یک‌بار)
docker compose exec backend python -m app.scripts.init_db

# ۴. بررسی
docker compose ps
curl http://localhost:8000/api/health
# داشبورد: http://localhost:3000
```

## دستورات روزمره

| کار | دستور |
|-----|--------|
| لاگ بک‌اند | `docker compose logs -f backend` |
| توقف | `docker compose down` |
| توقف + حذف volume دیتابیس | `docker compose down -v` |
| rebuild پس از تغییر کد | `docker compose up -d --build backend frontend` |

## متغیرهای محیطی در Docker

- فایل واحد **`.env` در ریشه** — توسط `env_file` به `backend` تزریق می‌شود.
- لیست کامل کلیدها: `11_IMPLEMENTATION_GUIDE.md`.
- **هرگز** `.env` را commit نکنید؛ فقط `.env.example`.

## حجم‌های پایدار (Volumes)

| مسیر در container | محتوا |
|-------------------|--------|
| `pgdata` (named volume) | PostgreSQL |
| `/app/data/ledger` | داستان معامله — `13` |
| `/app/data/historical` | OHLCV بک‌تست — `06` |
| `/app/data/audit_reports` | گزارش ممیزی هفتگی |

## ممیزی هفتگی در Docker

سرویس `scheduler` (یا `docker compose run --rm backend python scripts/weekly_audit.py` در cron host):

```yaml
  scheduler:
    build: ./backend
    env_file: .env
    command: ["python", "-m", "app.scripts.weekly_audit"]
    profiles: ["tools"]
    depends_on:
      postgres: { condition: service_healthy }
```

اجرای دستی: `docker compose --profile tools run --rm scheduler`

> **Guardrail:** `scheduler` فقط پیشنهاد (`PENDING`) می‌سازد — **هرگز** `apply_prompt_tuning` را مستقیم صدا نزند. اعمال فقط از UI — `13` بخش د.

## پیش‌نیاز میزبان

- **Docker Engine** 24+ و **Docker Compose** v2 (`docker compose`)
- فقط برای build: دسترسی اینترنت (pull image + npm/pip در Dockerfile)

Python/Node روی میزبان **لازم نیست** اگر فقط با Compose کار می‌کنید.

## اسناد مرتبط

- env و فازبندی: `11_IMPLEMENTATION_GUIDE.md`
- درخت فایل: `09_PROJECT_TREE.md`
- معماری: `01_ARCH_OVERVIEW.md`
