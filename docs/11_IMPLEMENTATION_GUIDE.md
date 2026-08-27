# ۱۱ — راهنمای پیاده‌سازی (بدون ابهام)

## استقرار: Docker (اجباری به‌عنوان روش رسمی)

**کل سیستم** — PostgreSQL، Redis، بک‌اند FastAPI، فرانت‌اند Next.js — با **`docker compose`** اجرا می‌شود. مرجع کامل: **`14_DOCKER_DEPLOYMENT.md`**.

```bash
cp .env.example .env   # پر کردن کلیدها
docker compose up -d --build
```

نصب جداگانهٔ Python/Node فقط برای توسعهٔ محلی اختیاری است (بخش «راه‌اندازی بدون Docker» پایین).

## پیش‌نیازها

- **Docker Engine 24+** و **Docker Compose v2**
- حساب **Testnet** صرافی (Bybit یا Binance)
- API key: **OpenRouter** (تک درگاه LLM) + CryptoPanic + Testnet صرافی
- **اجباری:** مطالعه `12_COST_OPTIMIZATION.md` قبل از wiring ایجنت‌ها

## ساختار ریشه پروژه

```
neuroTrade/          # یا ai-trading-bot/
├── docs/            # همین پوشه
├── backend/
└── frontend/
```

## متغیرهای محیطی

### `backend/.env`

```env
# Database
# در Docker (پیش‌فرض compose):
# DATABASE_URL=postgresql+asyncpg://neurotrade:PASS@postgres:5432/neurotrade
# REDIS_URL=redis://redis:6379/0
# روی میزبان (dev بدون container بک‌اند):
DATABASE_URL=postgresql+asyncpg://neurotrade:pass@localhost:5432/neurotrade
REDIS_URL=redis://localhost:6379/0

# Exchange (Testnet)
EXCHANGE_ID=bybit
EXCHANGE_API_KEY=
EXCHANGE_SECRET=
EXCHANGE_SANDBOX=true

# LLM — OpenRouter واحد (07_EXTERNAL_SERVICES)
OPENROUTER_API_KEY=
STRATEGIST_MODEL=anthropic/claude-3.5-sonnet
SENTIMENT_MODEL=deepseek/deepseek-v3
DECISION_MODEL=anthropic/claude-3.5-sonnet
LLM_FALLBACK_MODEL=deepseek/deepseek-r1
AUDIT_MODEL=anthropic/claude-3.5-sonnet

# News
CRYPTOPANIC_TOKEN=

# Telegram (اختیاری)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# App — فرکانس از تایم‌فریم (نه 300 ثابت برای 1h)
DEFAULT_TICKER=BTC/USDT
DEFAULT_TIMEFRAME=1h
# برای 1h خودکار 900؛ override دستی:
# CYCLE_INTERVAL_SECONDS=900
ZONE_GATE_BUFFER_PCT=0.001
TICKER_POLL_SECONDS=120
CORS_ORIGINS=http://localhost:3000
```

### `frontend/.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/dashboard
```

## راه‌اندازی بدون Docker (فقط توسعه — اختیاری)

اگر فقط یک سرویس را دیباگ می‌کنید، DB/Redis را همچنان با Compose بالا بیاورید:

```bash
docker compose up -d postgres redis
```

سپس بک‌اند/فرانت را روی میزبان (نیاز: Python 3.11+، Node 20+):

```bash
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

## چک‌لیست Docker (فاز A)

- [ ] `docker-compose.yml` + `backend/Dockerfile` + `frontend/Dockerfile`
- [ ] `.env.example` در ریشه — `DATABASE_URL` با host `postgres`
- [ ] `docker compose up -d --build` — هر چهار سرویس healthy
- [ ] `init_db` داخل container — جداول `04`

## ترتیب شروع پیشنهادی (Risk یا Exchange؟)

**اول: خط لوله داده + صرافی (فاز A → B)**، بعد **Risk Engine (فاز B+)**.

| ترتیب | دلیل |
|-------|------|
| ۱. `config` + `database` + health | زمینه اجرا |
| ۲. `exchange.py` + `retriever` | `fetch_ohlcv` / `fetch_balance` ورودی Zone Gate و `calculate_position_size` |
| ۳. `risk.py` + تست واحد | فرمول‌های `03` با قیمت/بالانس mock و سپس balance واقعی testnet |
| ۴. `zone_trigger` → LLM → graph | بدون داده زنده، Gate و ایجنت معنا ندارند |

Risk را **موازی** می‌توانی با تست‌های خالص (بدون CCXT) شروع کنی، اما **یکپارچه‌سازی** بعد از Exchange منطقی‌تر است چون `position_size` به `account_balance` واقعی نیاز دارد.

---

## فازبندی توسعه (چک‌لیست)

### فاز A — اسکلت بک‌اند
- [ ] `config.py` — لود env با Pydantic Settings
- [ ] `core/database.py` — SQLAlchemy async + جداول `04`
- [ ] `GET /api/health`, `GET/PATCH /api/settings`
- [ ] ردیف پیش‌فرض `system_settings` با `is_active=false`

### فاز B — صرافی و Retriever
- [ ] `core/exchange.py` — CCXT async + rate limit 500ms
- [ ] نود `retrieve_data` در LangGraph (بدون LLM)
- [ ] Cron/APScheduler هر `CYCLE_INTERVAL_SECONDS`

### فاز B+ — Risk Engine (قطعی)
- [ ] `core/risk.py` — `calculate_position_size` + Pydantic validator طبق `03`
- [ ] تست واحد: LONG/SHORT نامعتبر SL → رد
- [ ] اتصال `fetch_balance()` از exchange در مسیر اجرا

### فاز C — Zone Gate + ایجنت‌ها
- [ ] `core/zone_trigger.py` — Pandas، `should_invoke_llm()` طبق `12`
- [ ] `core/llm_client.py` — `AsyncOpenAI` + OpenRouter (07)
- [ ] `agents/graph.py` — retrieve → **zone_gate** → (hit) strategist ∥ sentiment → decision
- [ ] `config.resolve_cycle_interval()` — `1h`=900s، `4h`=1800s
- [ ] پرامپت‌های `08` — بدون LLM وقتی `zone_hit=false`

### فاز D — API و WebSocket
- [ ] `POST /api/emergency/kill-switch`
- [ ] approve/reject signals
- [ ] WebSocket + Redis pub/sub — رویدادهای `10`
- [ ] ذخیره `agent_signals` و `trade_positions`

### فاز E — فرانت‌اند
- [ ] shadcn/ui طبق `05`
- [ ] `WebSocketContext.tsx`
- [ ] صفحات: `/`, `/signals`, `/analytics`, `/settings`
- [ ] `ApprovalModal` روی `SIGNAL_APPROVAL_REQUEST`

### فاز F — بک‌تست
- [ ] `backtest/engine.py` — قوانین `06`
- [ ] دانلود OHLCV به `data/historical/`

### فاز G — Post-Mortem + Guardrail پرامپت
- [ ] `core/trade_ledger.py` — `data/ledger/{trade_id}.json` + `trade_ledger`
- [ ] `scripts/weekly_audit.py` — فقط `prompt_change_proposals` (PENDING) + `market_regime`
- [ ] `prompts/baseline/` + `prompts/active/` — جدا از هم
- [ ] `POST /api/prompt-proposals/{id}/approve|reject` + `rollback` — `10`
- [ ] `apply_prompt_tuning.py` — **فقط** از handler Approve؛ ممنوع در cron
- [ ] `PROMPT_TUNING_REQUEST` WebSocket + صفحه `/settings/prompt-tuning` — `05`
- [ ] تست: ممیزی هفته ANOMALOUS → بدون Approve پرامپت active تغییر نکند

## تعریف «Done» برای MVP

1. چرخه ۵ دقیقه‌ای روی Testnet بدون خطای Pydantic
2. حالت SEMI: مودال تأیید → approve → اردر واقعی در testnet
3. Kill-Switch: بستن پوزیشن‌ها + `SUSPENDED`
4. داشبورد: وضعیت ایجنت + پوزیشن‌های باز + daily drawdown

## تست دستی حیاتی

| سناریو | انتظار |
|--------|--------|
| SL بالاتر از entry برای LONG | Risk رد کند، لاگ در DB |
| daily drawdown ≥ 3% | `is_active` خودکار false تا فردا |
| قطع WS | UI reconnect بدون crash |
| reject signal | هیچ اردری به صرافی نرود |

## نکات Cursor

- همیشه `@docs/11_IMPLEMENTATION_GUIDE.md` + سند موضوع فعلی را cite کن
- هر PR/feature یک فاز از چک‌لیست بالا
- **هرگز** Withdrawal را در API Key صرافی فعال نکن
