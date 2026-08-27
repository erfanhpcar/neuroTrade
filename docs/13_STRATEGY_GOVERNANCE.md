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

تغییر parameter یا rule که behavior را عوض می‌کند = version جدید؛ overwrite نسخه فعال ممنوع.

## Coding Agent Governance

Cursor/Codex قبل از تغییر Strategy semantics، Risk assumptions مرتبط، یا promotion criteria باید:

1. `AGENTS.md` و اسناد `02`, `03`, `06`, `13`, `16` را بخوانند؛
2. مشخص کنند تغییر **bug fix** است یا **hypothesis/strategy change**؛
3. اثر تغییر روی reproducibility، OOS و regression tests را در plan بیاورند؛
4. اگر behavior جدید قبلاً در docs تصویب نشده، قبل از implementation تصمیم را مطرح کنند.

Coding agent حق ندارد برای بهتر کردن یک backtest مشخص، parameter/rule را تکراری tune کند و همان dataset را evidence نهایی معرفی کند. اگر OOS پس از مشاهده نتیجه برای tuning استفاده شود، دیگر OOS نهایی محسوب نمی‌شود و evaluation تازه لازم است.

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

یک یا چند معامله ضررده نباید مستقیماً باعث تغییر production rule شود. یافته ابتدا hypothesis است و باید دوباره از Research/OOS/Paper pipeline عبور کند.

## تغییر Strategy

یافته‌های research یا AI فقط hypothesis/proposal ایجاد می‌کنند. قبل از فعال شدن باید دوباره از pipeline سند `06_BACKTESTING.md` عبور کنند.

حداقل checks برای strategy change:

- deterministic replay
- no-look-ahead regression
- OOS evaluation
- parameter sensitivity در صورت تغییر پارامتر
- realistic costs
- comparison با baseline قبلی

## Rollback

فعال‌سازی strategy version باید atomic باشد و rollback به نسخه قبلی بدون تغییر تاریخچه ممکن باشد. Tradeهای تاریخی همیشه strategy/config version واقعی زمان معامله را نگه می‌دارند.

## Circuit breaker پژوهشی

اگر live behavior از validation envelope خارج شد — برای مثال drawdown، slippage یا failure rate شدیدتر از limit — سیستم باید `HALTED` شود یا strategy غیرفعال شود؛ نه اینکه خودکار parameter را optimize کند.

## AI

AI می‌تواند post-mortem یا hypothesis پیشنهاد دهد، اما active strategy/Risk را خودکار تغییر نمی‌دهد. جزئیات: `08_AI_EXTENSION.md`.
