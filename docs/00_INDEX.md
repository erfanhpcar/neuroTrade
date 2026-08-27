# neuroTrade — فهرست مستندات

این پوشه **Single Source of Truth** پروژه است. هدف پروژه از این نسخه به بعد ساخت یک **Quant/Systematic Trading Platform** است؛ نه یک AI Trading Bot.

## اصول قفل‌شده

1. هسته تصمیم‌گیری معاملاتی در V0/V1 **کاملاً deterministic** و قابل بک‌تست است.
2. همان Strategy Engine باید هم در Backtest و هم در Live/Paper استفاده شود.
3. Strategy فقط `Signal` تولید می‌کند؛ Risk Engine درباره حجم، اجازه/رد و محدودیت‌های حساب تصمیم می‌گیرد.
4. Execution Engine از Strategy جداست و تمام idempotency، precision، fee، slippage، retry و reconciliation را مدیریت می‌کند.
5. PostgreSQL منبع حقیقت تراکنشی است؛ Redis فقط cache/pub-sub/lock است؛ OHLCV تاریخی در Parquet نگه‌داری می‌شود.
6. AI در MVP الزامی نیست و حق دور زدن Risk/Execution را ندارد.
7. توسعه به ترتیب `Research → Backtest → Paper → Testnet/SEMI → Live` انجام می‌شود.
8. معماری به صرافی خاص وابسته نیست؛ Market Data Provider و Execution Provider آداپتر دارند.

## نقشه اسناد

| فایل | موضوع |
|---|---|
| `01_ARCH_OVERVIEW.md` | معماری کلان، Control Plane / Trading Worker، تکنولوژی‌ها |
| `02_STRATEGY_ENGINE.md` | قرارداد Strategy، Signal، Strategy Versioning، استراتژی V1 |
| `03_RISK_FIREWALL.md` | Risk Engine، Position Sizing، HALT/FLATTEN، محدودیت‌های سخت |
| `04_DATA_SCHEMAS.md` | PostgreSQL schema، Parquet، idempotency |
| `05_DASHBOARD_UI.md` | Next.js dashboard، صفحات و کنترل‌های عملیاتی |
| `06_BACKTESTING.md` | Backtest واقعی، OOS، Walk-Forward، Promotion Gates |
| `07_EXTERNAL_SERVICES.md` | Market Data، صرافی، The True Trade، CCXT، API keys |
| `08_AI_EXTENSION.md` | AI اختیاری در فازهای آینده؛ خارج از مسیر اجرای معامله |
| `09_PROJECT_TREE.md` | ساختار پیشنهادی monorepo |
| `10_REST_API.md` | REST/WebSocket contract |
| `11_IMPLEMENTATION_GUIDE.md` | ترتیب ساخت و Definition of Done |
| `12_API_COST_RATE_LIMITS.md` | هزینه داده، rate limit، WebSocket/REST policy |
| `13_STRATEGY_GOVERNANCE.md` | نسخه‌بندی، promotion، post-mortem، rollback |
| `14_DOCKER_DEPLOYMENT.md` | Docker Compose و سرویس‌ها |
| `15_CURSOR_IMPLEMENTATION_CHECKLIST.md` | چک‌لیست اجرایی گام‌به‌گام برای Cursor |

## ترتیب پیاده‌سازی

```text
0. Skeleton + Docker + CI
1. Market Data + Historical Storage
2. Strategy Engine V1
3. Deterministic Backtest + Metrics
4. Risk + Portfolio
5. Paper Execution + Reconciliation
6. FastAPI + WebSocket + Dashboard
7. Exchange Testnet / SEMI
8. Live hardening
9. AI research extensions (اختیاری)
```

## تصمیم‌های فعلی فناوری

| لایه | تصمیم |
|---|---|
| Backend | Python 3.11+ / FastAPI |
| Trading process | Worker مستقل از HTTP API |
| Frontend | Next.js App Router + Tailwind + shadcn/ui |
| DB | PostgreSQL |
| Cache/Realtime | Redis |
| Historical market data | Parquet |
| Exchange abstraction | Adapter؛ CCXT در صورت پشتیبانی، native adapter در غیر این صورت |
| Initial public market data | Bybit/Binance public REST + WebSocket |
| Planned account execution | Adapter برای The True Trade پس از اعتبارسنجی مستندات API |
| AI | خاموش/اختیاری در MVP |
| Deployment | Docker Compose |

> وضعیت فعلی مخزن: فاز طراحی. قبل از ایجاد کد اجرایی، اسناد 00 تا 15 باید مرجع Cursor باشند.
