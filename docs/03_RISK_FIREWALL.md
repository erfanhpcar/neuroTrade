# 03 — Risk Firewall

Risk Engine کاملاً deterministic است و هیچ Strategy یا AI حق دور زدن آن را ندارد.

## مسئولیت‌ها

- position sizing
- max risk per trade
- max portfolio exposure
- max open positions
- max daily loss / drawdown lock
- correlated exposure limits
- volatility-aware sizing
- reject malformed/stale signals

## Position sizing

فرمول پایه:

```text
allowed_loss = equity * risk_pct
risk_per_unit = abs(entry - stop)
raw_size = allowed_loss / risk_per_unit
```

در پیاده‌سازی واقعی باید fee، expected slippage، contract multiplier، leverage rules، quantity step و min/max notional لحاظ شود.

## Hard limits اولیه

- default risk per trade: `0.5%`
- hard max risk per trade: `1.0%` تا زمانی که داده کافی برای تغییر وجود نداشته باشد
- max daily realized + unrealized loss: configurable با سقف سخت
- max concurrent positions: configurable
- max aggregate open risk: configurable

اعداد نهایی باید از config versioned بیایند و تغییرشان audit شود.

## فرمان‌های اضطراری

### HALT

- ساخت signal جدید می‌تواند ادامه یابد اما execution جدید ممنوع است.
- pending entry orders طبق policy لغو می‌شوند.
- positionهای باز خودکار market-close نمی‌شوند مگر policy صریح.

### FLATTEN_ALL

- cancel تمام pending orders
- close تمام positions طبق safe execution policy
- state → `HALTED`
- نیازمند تأیید دو مرحله‌ای در UI

## RiskDecision

```text
APPROVED | REJECTED
reason_codes[]
calculated_size
estimated_risk_usd
estimated_risk_pct
portfolio_open_risk_pct
```

## تست‌های حیاتی

- LONG با stop >= entry رد شود.
- SHORT با stop <= entry رد شود.
- stale signal رد شود.
- size بعد از rounding از hard max عبور نکند.
- fee/slippage budget در worst-case لحاظ شود.
- daily lock حتی بعد از restart حفظ شود.
- race condition دو signal همزمان نتواند exposure limit را دور بزند.
