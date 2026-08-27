# 08 — AI Extension (Future / Optional)

AI در MVP جزو مسیر تولید یا اجرای معامله نیست.

## کاربردهای مجاز آینده

- توضیح human-readable یک Signal قطعی
- post-mortem معاملات
- خلاصه‌سازی نتایج backtest
- research assistant برای مقایسه experimentها
- anomaly explanation
- پیشنهاد hypothesis جدید برای تست

## کاربردهای ممنوع در هسته

- تعیین مستقیم BUY/SELL بدون Strategy rule
- تغییر Risk limits در runtime
- تغییر خودکار strategy active پس از یک هفته بد/خوب
- ارسال order مستقیم
- live self-learning

## A/B policy

اگر در آینده AI filter اضافه شد، باید یک baseline بدون AI حفظ شود:

```text
Quant Baseline
vs
Same Quant Strategy + AI Advisory Filter
```

فقط با OOS/forward evidence می‌توان AI را promote کرد. هزینه API، latency و failure rate نیز جزو معیار مقایسه است.

## Fail-safe

در unavailable بودن AI، مسیر deterministic باید بتواند طبق mode تعریف‌شده ادامه دهد یا HALT شود؛ AI outage نباید state معامله را خراب کند.
