# 01 — Architecture Overview

## هدف

neuroTrade یک **Quant/Systematic Trading Platform** است. هسته معامله با قوانین قابل اندازه‌گیری و قابل تکرار کار می‌کند؛ LLM جزو مسیر اجباری تصمیم‌گیری نیست.

## معماری کلان

```text
Next.js Dashboard
      │ REST / WebSocket
      ▼
FastAPI Control Plane ───── PostgreSQL
      │                      ▲
      │                      │
      └──── Redis Pub/Sub ───┤
                             │
                    Trading Worker
                    ├─ Market Data
                    ├─ Strategy Engine
                    ├─ Portfolio Engine
                    ├─ Risk Engine
                    ├─ Execution Engine
                    └─ Reconciliation
                             │
                       Exchange Adapter
                             │
                   Bybit / Binance / TTT
```

## اصل جداسازی Control Plane و Data Plane

FastAPI مسئول HTTP/WS، تنظیمات، مشاهده تاریخچه، شروع Backtest و فرمان‌های اپراتور است. حلقه معاملات در process مستقل `trading-worker` اجرا می‌شود. Restart شدن API نباید باعث توقف یا تکرار ناخواسته Order شود.

## موتورهای اصلی

1. **Market Data Engine**: دریافت/نرمال‌سازی OHLCV، ticker، trades و در صورت نیاز order book/funding/OI.
2. **Strategy Engine**: تولید Signal بدون دسترسی مستقیم به صرافی و بدون تعیین حجم نهایی.
3. **Portfolio Engine**: exposure، equity، positions و realized/unrealized PnL.
4. **Risk Engine**: approve/reject، position sizing و hard limits.
5. **Execution Engine**: تبدیل OrderIntent به سفارش واقعی/شبیه‌سازی‌شده، idempotency و precision.
6. **Reconciliation Engine**: تطبیق DB با وضعیت واقعی صرافی.
7. **Backtest Engine**: اجرای همان Strategy + Risk interface روی داده تاریخی.

## Deployment style

نسخه اولیه **Modular Monolith + Worker** است، نه Microservices. تا زمانی که scaling واقعی نیاز نشده، جداسازی deployment سرویس‌ها ممنوع است مگر دلیل اندازه‌گیری‌شده وجود داشته باشد.

## State ownership

- PostgreSQL: Source of Truth برای signal/order/fill/position/risk/settings/backtests.
- Redis: cache، pub/sub، distributed lock و latest snapshots؛ قابل بازسازی.
- Exchange: حقیقت نهایی برای وضعیت واقعی balance/order/position در live.
- Parquet: historical market data و datasetهای research.

## Operational modes

- `PAPER`: هیچ order واقعی ارسال نمی‌شود.
- `SEMI`: Signal + Risk → تأیید اپراتور → Execution.
- `FULL`: Signal + Risk → Execution مستقیم؛ فقط پس از promotion رسمی.
- `HALTED`: order جدید ممنوع؛ positionهای موجود طبق policy مدیریت می‌شوند.

## Non-goals در MVP

- HFT / sub-second trading
- تصمیم مستقیم LLM برای معامله
- self-learning live
- microservice architecture
- وابستگی به یک exchange خاص
