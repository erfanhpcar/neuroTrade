# 13 — Strategy Governance & Post-Mortem

## Strategy lifecycle

```text
IDEA
→ RESEARCH
→ OOS_VALIDATED
→ PAPER
→ SEMI
→ LIVE_LIMITED
→ LIVE
→ RETIRED
```

هیچ انتقال stage خودکار نیست.

## Versioning

هر strategy release باید شامل این‌ها باشد:

- strategy name/version
- parameter config hash
- code commit SHA
- dataset hash
- backtest run IDs
- promotion note
- approved_at / approved_by

تغییر parameter یا rule = version جدید؛ overwrite نسخه فعال ممنوع.

## Post-mortem

بعد از معاملات و دوره‌های paper/live، سیستم باید facts را ثبت کند:

- signal + strategy version
- risk decision
- order/fill sequence
- fees/funding/slippage
- market snapshot references
- realized outcome
- reconciliation/anomaly events

تحلیل انسانی یا AI بعداً می‌تواند روی این facts کار کند، اما history تغییر نمی‌کند.

## تغییر Strategy

یافته‌های research یا AI فقط hypothesis/proposal ایجاد می‌کنند. قبل از فعال شدن باید دوباره از pipeline سند 06 عبور کنند.

## Rollback

فعال‌سازی strategy version باید atomic باشد و rollback به نسخه قبلی بدون تغییر تاریخچه ممکن باشد.

## Circuit breaker پژوهشی

اگر live behavior از validation envelope خارج شد — برای مثال drawdown، slippage یا failure rate شدیدتر از limit — سیستم باید `HALTED` شود یا strategy غیرفعال شود؛ نه اینکه خودکار parameter را optimize کند.
