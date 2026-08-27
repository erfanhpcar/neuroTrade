# neuroTrade — فهرست مستندات

این پوشه **منبع حقیقت (Single Source of Truth)** پروژه است. هنگام پیاده‌سازی در Cursor، کل پوشه `docs/` را با `@` به کانتکست اضافه کنید.

## نقشه اسناد

| فایل | موضوع | زمان مطالعه |
|------|--------|-------------|
| [01_ARCH_OVERVIEW.md](./01_ARCH_OVERVIEW.md) | معماری کلان، پشته فناوری، دیاگرام لایه‌ها | قبل از هر کدی |
| [02_AGENT_PROTOCOLS.md](./02_AGENT_PROTOCOLS.md) | **استراتژی S/D**، Fresh Zones، Confluence، LangGraph State | فاز بک‌اند ایجنت |
| [13_POST_MORTEM_REFLECTION.md](./13_POST_MORTEM_REFLECTION.md) | Ledger، ممیزی هفتگی، Prompt Tuning (**بدون Live Learning**) | پس از MVP / فاز G |
| [12_COST_OPTIMIZATION.md](./12_COST_OPTIMIZATION.md) | **هزینه API <۲۰$/ماه** — فرکانس، ماشه زون، DeepSeek | **قبل از فعال‌سازی LLM** |
| [03_RISK_FIREWALL.md](./03_RISK_FIREWALL.md) | فرمول پوزیشن‌سایز، خطوط قرمز، Kill-Switch | همزمان با `core/risk.py` |
| [04_DATA_SCHEMAS.md](./04_DATA_SCHEMAS.md) | جداول PostgreSQL، پکت‌های WebSocket | فاز دیتابیس + WS |
| [05_DASHBOARD_UI.md](./05_DASHBOARD_UI.md) | Next.js، shadcn/ui، صفحات و کامپوننت‌ها | فاز فرانت‌اند |
| [06_BACKTESTING.md](./06_BACKTESTING.md) | بک‌تست هیبرید، متریک‌ها | فاز بک‌تست |
| [07_EXTERNAL_SERVICES.md](./07_EXTERNAL_SERVICES.md) | CCXT، CryptoPanic، LLM، تلگرام | فاز یکپارچه‌سازی |
| [08_PROMPT_DICTIONARY.md](./08_PROMPT_DICTIONARY.md) | System Prompt و JSON Schema هر ایجنت | فاز ایجنت |
| [09_PROJECT_TREE.md](./09_PROJECT_TREE.md) | ساختار درختی فایل‌های پروژه | همیشه مرجع |
| [10_REST_API.md](./10_REST_API.md) | قرارداد REST + WebSocket + TypeScript types | فاز API |
| [11_IMPLEMENTATION_GUIDE.md](./11_IMPLEMENTATION_GUIDE.md) | ترتیب ساخت، env، چک‌لیست آماده‌سازی | **شروع پیاده‌سازی** |
| [14_DOCKER_DEPLOYMENT.md](./14_DOCKER_DEPLOYMENT.md) | **اجرای کل سیستم با Docker Compose** (روش رسمی) | قبل از اولین `docker compose up` |

> **سیاست هزینه:** Claude فقط پس از `zone_gate` — جزئیات اجباری در `12_COST_OPTIMIZATION.md`.

> **توجه:** فایل `SYSTEM_DESIGN.md` نسخه اولیه همان محتوای `01_ARCH_OVERVIEW.md` است؛ برای جلوگیری از ابهام فقط `01` را به‌روز نگه دارید.

## ترتیب پیشنهادی پیاده‌سازی

```
۰. Docker Compose (کل استک)              → 14_DOCKER_DEPLOYMENT
۱. زیرساخت (PostgreSQL, Redis, .env)     → 11 + 14
۲. core: database, exchange, risk        → 03, 04, 07
۳. zone_trigger + agents + llm_router  → 02, 08, 12
۴. api REST + WebSocket                  → 10, 04
۵. frontend با shadcn                    → 05, 10
۶. backtest                              → 06
۷. ledger + ممیزی هفتگی (آفلاین)        → 13
```

## تصمیم‌های معماری قفل‌شده (بدون بحث مجدد در کد)

| موضوع | تصمیم |
|--------|--------|
| بک‌اند | Python 3.11+ / FastAPI / LangGraph |
| فرانت‌اند | Next.js 14+ App Router / Tailwind / **shadcn/ui** |
| دیتابیس | PostgreSQL (+ Redis برای WS broadcast) |
| صرافی (تست) | Bybit Testnet یا Binance Testnet via CCXT |
| حالت معامله | `SEMI` (پیش‌فرض) یا `FULL` |
| ریسک هر ترید | پیش‌فرض ۱٪، سقف سخت ۱.۵٪ |
| فرکانس چرخه | `1h` → هر ۱۵ دقیقه؛ `4h` → هر ۳۰ دقیقه (`12`) |
| فراخوانی LLM | فقط پس از Zone Gate (Pandas) — Claude = Decision trigger |
| LLM | **فقط OpenRouter** — `core/llm_client.py` — مدل‌ها از env |
| بودجه LLM | هدف **۱۵–۲۰$/ماه** + Zone Gate — `12` |
| یادگیری AI | **Post-Mortem فقط** — Ledger + ممیزی — `13`؛ Live Learning ممنوع |
| تغییر پرامپت | **فقط با Approve دستی در UI** — Guardrail overfitting — `13` §د |
| استراتژی | Supply/Demand، Fresh Zones، امتیاز زون، Confluence LTF — `02` بخش ۰ |
| استقرار / اجرا | **Docker Compose** — postgres، redis، backend، frontend — `14` |

## ناسازگاری‌هایی که در اسناد یکسان شدند

- **Data Retriever** در معماری یک **نود غیر-LLM** در LangGraph است (واکشی CCXT + CryptoPanic)، نه ایجنت با پرامپت — جزئیات در `02_AGENT_PROTOCOLS` بخش ۴.
- **Risk Engine** جدا از ایجنت Decision است؛ AI فقط پیشنهاد می‌دهد، اجرا فقط پس از Pydantic + Risk Firewall.
