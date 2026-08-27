# ۰۱ — نمای کلی معماری (Architecture Overview)

> این سند معادل رسمی `SYSTEM_DESIGN.md` است. برای یکپارچگی نام‌گذاری فقط از `01_ARCH_OVERVIEW.md` استفاده کنید.

## ۱. ساختار کلان (High-Level Architecture)

سیستم **دکاپل** است: هسته AI/معاملات در **Python (FastAPI)** و داشبورد در **Next.js**. ارتباط: **REST** (تنظیمات، تاریخچه) + **WebSocket** (رویداد زنده).

> **استقرار:** کل پلتفرم با **Docker Compose** بالا می‌آید (postgres، redis، backend، frontend) — جزئیات و دستورات در `14_DOCKER_DEPLOYMENT.md`. این روش رسمی اجراست؛ نصب پراکندهٔ سرویس‌ها روی میزبان توصیه نمی‌شود.

```
┌─────────────────────────────────────────────────────────────┐
│           Frontend Dashboard (Next.js + shadcn/ui)          │
│  Kill-Switch │ Semi/Full │ Signals │ Analytics │ Settings   │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST + WebSocket
┌───────────────────────────▼─────────────────────────────────┐
│              Backend AI Engine (FastAPI)                     │
│  Zone Gate (Pandas) → LLM فقط با ماشه │ Risk │ CCXT         │
│  PostgreSQL │ Redis (pub/sub for WS)                        │
└───────────────┬─────────────────────────────┬───────────────┘
                │                             │
        ┌───────▼────────┐            ┌───────▼────────┐
        │ Data + News    │            │ Exchange       │
        │ CCXT OHLCV     │            │ Testnet/Live   │
        │ CryptoPanic    │            │ via CCXT       │
        └────────────────┘            └────────────────┘
```

## ۲. پشته فناوری

| لایه | فناوری | دلیل |
|------|--------|------|
| فرانت‌اند | Next.js App Router + Tailwind + **shadcn/ui** | کامپوننت‌های دسترس‌پذیر، تم دارک، Dialog/Table برای داشبورد ترید |
| بک‌اند | FastAPI (async) | اکوسیستم AI، WebSocket، سرعت |
| ایجنت‌ها | LangGraph | گراف حلقوی، State مشترک |
| DB | PostgreSQL | سیگنال‌ها، پوزیشن‌ها، تنظیمات |
| کش / WS | Redis | Pub/Sub برای broadcast به چند کلاینت |
| صرافی | CCXT async | یک API برای چند صرافی |
| LLM | **OpenRouter** (`AsyncOpenAI`) — مدل‌ها فقط از env | هدف <۲۰$/ماه — `07`, `12` |
| Zone Gate | Pandas در `core/zone_trigger.py` | رد ~۹۰٪ چرخه‌ها قبل از LLM |

## ۳. زیرسیستم چندعاملی

| # | نام | نوع | وظیفه |
|---|-----|-----|--------|
| 0 | Data Retriever | **کد پایتون** (بدون LLM) | `fetch_ohlcv`, `fetch_order_book`, LTF candles، اخبار |
| 0b | Zone Gate | **Pandas** | آیا قیمت در زون S/D است؟ اگر نه → پایان چرخه |
| 1 | Technical Strategist | LLM | S/D، Fresh Zones (RBD/DBR)، Confluence LTF — `02` §۰، `08` |
| 2 | Sentiment Analyst | LLM (mini/DeepSeek) | فقط پس از Gate — `08` |
| 3 | Decision Agent | **Claude (Trigger)** | BUY/SELL/HOLD — فقط پس از Gate — `08` |
| — | Risk Firewall | **کد قطعی** | پوزیشن‌سایز، اعتبارسنجی SL/TP، اجرا CCXT |

جریان داده: Retriever → **Zone Gate** → (اگر hit) Strategist ∥ Sentiment → Decision (Claude) → Risk → Exchange.  
فرکانس: `1h` = هر ۱۵ دقیقه، `4h` = هر ۳۰ دقیقه — `12_COST_OPTIMIZATION.md`.

## ۴. حالت‌های عملیاتی

| حالت | `trading_mode` | رفتار |
|------|----------------|--------|
| خاموش | `is_active=false` | هیچ چرخه‌ای اجرا نمی‌شود |
| نیمه‌اتومات | `SEMI` | پس از Risk، `SIGNAL_APPROVAL_REQUEST` به UI |
| تمام‌اتومات | `FULL` | اجرای مستقیم پس از Risk |
| تعلیق | `SUSPENDED` | پس از Kill-Switch تا فعال‌سازی دستی |

## ۵. امنیت (Risk Firewall — خلاصه)

جزئیات در `03_RISK_FIREWALL.md`:

1. API Key صرافی: **بدون Withdrawal**
2. سقف ضرر روزانه ۳٪ — توقف تا نیمه‌شب UTC
3. حداکثر ۳ پوزیشن باز همزمان
4. اعتبارسنجی Pydantic قبل از `create_order`

## ۶. اسناد مرتبط

- ایجنت‌ها و State: `02_AGENT_PROTOCOLS.md`
- API و WS: `10_REST_API.md`
- UI: `05_DASHBOARD_UI.md`
- شروع کار: `11_IMPLEMENTATION_GUIDE.md`
- هزینه API: `12_COST_OPTIMIZATION.md`
- استراتژی S/D: `02_AGENT_PROTOCOLS.md` بخش ۰
- یادگیری Post-Mortem: `13_POST_MORTEM_REFLECTION.md`
- Docker: `14_DOCKER_DEPLOYMENT.md`
