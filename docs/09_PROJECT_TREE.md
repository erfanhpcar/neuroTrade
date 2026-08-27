این سند ساختار دقیق فولدرها و فایل‌های کل پروژه (منورپو شامل بک‌اند و فرانت‌اند) را مشخص می‌کند تا پیاده‌سازی گام‌به‌گام در کرسر بدون تداخل ساختاری انجام شود.

Plaintext

```
neuroTrade/                   # ریشه اصلی پروژه
├── docker-compose.yml        # استقرار رسمی — postgres, redis, backend, frontend (14)
├── docker-compose.override.yml
├── .env.example
├── docs/                     # مستندات معماری (۰۰ تا ۱۴)
│   ├── 00_INDEX.md           # فهرست + ترتیب پیاده‌سازی
│   ├── 01_ARCH_OVERVIEW.md
│   ├── 02_AGENT_PROTOCOLS.md
│   ├── 03_RISK_FIREWALL.md
│   ├── 04_DATA_SCHEMAS.md
│   ├── 05_DASHBOARD_UI.md
│   ├── 06_BACKTESTING.md
│   ├── 07_EXTERNAL_SERVICES.md
│   ├── 08_PROMPT_DICTIONARY.md
│   ├── 09_PROJECT_TREE.md
│   ├── 10_REST_API.md
│   ├── 11_IMPLEMENTATION_GUIDE.md
│   ├── 12_COST_OPTIMIZATION.md
│   ├── 13_POST_MORTEM_REFLECTION.md
│   └── 14_DOCKER_DEPLOYMENT.md
│
├── backend/                  # موتور اصلی هوش مصنوعی و ریسک (Python / FastAPI)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # نقطه ورود بک‌اند و مدیریت کانکشن‌های WebSocket
│   │   ├── config.py         # لود کردن متغیرهای محیطی (.env) و خطوط قرمز ریسک
│   │   │
│   │   ├── core/
│   │   │   ├── database.py
│   │   │   ├── risk.py
│   │   │   ├── exchange.py
│   │   │   ├── llm_client.py     # AsyncOpenAI → OpenRouter (07)
│   │   │   ├── zone_trigger.py   # امتیاز زون + ماشه — قبل از LLM (02 §۰, 12)
│   │   │   └── trade_ledger.py   # داستان معامله پس از بستن پوزیشن (13)
│   │   │
│   │   ├── prompts/
│   │   │   ├── baseline/     # نسخه ثابت — مرجع Rollback
│   │   │   └── active/       # فقط پس از Approve UI (13 §د)
│   │   ├── agents/           # LangGraph + ایجنت‌ها
│   │   │   ├── graph.py
│   │   │   ├── retriever.py
│   │   │   ├── strategist.py
│   │   │   ├── sentiment.py
│   │   │   └── decision.py
│   │   │
│   │   ├── api/              # اندپوینت‌های REST برای فرانت‌اند
│   │   │   ├── settings.py   # تغییر وضعیت سیستم (Active/Semi/Full)
│   │   │   ├── signals.py    # لود کردن تاریخچه تصمیمات
│   │   │   ├── trades.py
│   │   └── prompt_proposals.py  # approve/reject/rollback — Human-in-the-loop
│   │   │
│   │   └── backtest/         # موتور تست استراتژی روی گذشته بازار
│   │       ├── engine.py     # شبیه‌ساز کندل‌ها و تطبیق اردرها
│   │       └── data_loader.py# لودر فایل‌های Parquet/CSV داده‌های تاریخی
│   │
│   ├── config/
│   │   └── agent_weights.yaml  # وزن Decision/Gate — بدون دست زدن به risk.py
│   ├── scripts/
│   │   ├── weekly_audit.py       # ممیزی آفلاین ضررها (13)
│   │   └── apply_prompt_tuning.py
│   ├── data/
│   │   ├── historical/       # OHLCV بک‌تست
│   │   ├── ledger/           # {trade_id}.json — داستان معامله
│   │   └── audit_reports/    # گزارش هفتگی ممیز
│   ├── Dockerfile            # تصویر سرویس backend
│   ├── requirements.txt
│   └── .env                  # در Docker از env_file ریشه تغذیه می‌شود
│
└── frontend/                 # داشبورد (Next.js + Tailwind + shadcn/ui)
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx    # تم dark + Sidebar + WebSocketProvider
    │   │   ├── page.tsx
    │   │   ├── signals/page.tsx
    │   │   ├── analytics/page.tsx
    │   │   └── settings/page.tsx
    │   ├── components/
    │   │   ├── ui/           # shadcn (button, dialog, table, ...)
    │   │   ├── layout/       # Sidebar, Header
    │   │   ├── AgentStatus.tsx
    │   │   ├── ActiveTrades.tsx
    │   │   ├── ApprovalModal.tsx
    │   │   ├── PromptTuningReview.tsx
    │   │   └── KillSwitch.tsx
    │   ├── context/
    │   │   └── WebSocketContext.tsx
    │   ├── lib/
    │   │   └── api.ts        # fetch wrapper برای REST (10_REST_API)
    │   └── types/
    │       └── index.ts      # تایپ‌های ۱:۱ با 10_REST_API
    ├── components.json       # پیکربندی shadcn
    ├── Dockerfile            # تصویر سرویس frontend
    ├── package.json
    ├── tailwind.config.ts
    └── .env.local            # در Compose از environment سرویس ست می‌شود

```

## 🚀 اتمام کامل فاز مستندسازی (The Blueprint is Ready!)

مانیفست شامل **۱۵ سند** (۰۰ تا ۱۴) در `docs/` است. اجرا: `14_DOCKER_DEPLOYMENT.md`. هزینه LLM: `12_COST_OPTIMIZATION.md`. نقطه شروع پیاده‌سازی: `00_INDEX.md` و `11_IMPLEMENTATION_GUIDE.md`. حالا پروژه شما از نظر معماری نرم‌افزار، کامل‌ترین زیرساخت را دارد.

وقتی این پروژه را در کرسر باز کنی، کافی است در بخش پرامپت یا با استفاده از `@` پوشه `docs/` را به کانتکست کرسر معرفی کنی. کرسر با خواندن این اسناد، کدهایی کاملاً منطبق بر معماری بدون خطا و با بالاترین سطح استاندارد تولید خواهد کرد.

