# 02 — Strategy Engine

## هدف

Strategy Engine باید deterministic، versioned، side-effect free و قابل اجرا روی Backtest/Paper/Live با یک قرارداد یکسان باشد.

## قرارداد اصلی

```python
class Strategy(Protocol):
    name: str
    version: str

    def generate_signal(
        self,
        market: MarketSnapshot,
        portfolio: PortfolioState,
    ) -> Signal | None:
        ...
```

Strategy حق ندارد مستقیم Order ارسال کند یا API صرافی را صدا بزند.

## Signal Contract

```text
Signal
- signal_id
- strategy_name
- strategy_version
- symbol
- timeframe
- side: LONG | SHORT | FLAT
- trigger_price
- stop_model
- exit_model
- created_at
- market_data_version / dataset_hash
- metadata
```

`position_size` نهایی متعلق به Risk Engine است.

## Strategy V1 پیشنهادی

نسخه اول Research بر پایه **volatility-adaptive trend following / time-series momentum** ساخته می‌شود. پارامترها باید config/version شوند، نه hardcode پراکنده.

اجزای فرضیه V1:

1. Universe filter بر اساس liquidity/volume.
2. Trend/momentum چندبازه‌ای.
3. Breakout trigger یا equivalent rule قابل اندازه‌گیری.
4. Volatility regime filter.
5. Exit rule مستقل و صریح.
6. No-trade conditions برای chop/extreme volatility.

این سند نتیجه سوددهی را تضمین نمی‌کند؛ V1 فقط اولین hypothesis است و باید Promotion Gates سند 06 را پاس کند.

## Strategy Plugins

```text
strategies/
├── base.py
├── trend_following/
│   ├── strategy.py
│   ├── config.py
│   └── tests/
├── mean_reversion/
└── supply_demand/   # hypothesis آینده، نه هسته MVP
```

## قواعد مهندسی

- هر strategy یک `strategy_version` immutable دارد.
- تغییر پارامتر = نسخه جدید.
- هر backtest باید strategy/config/dataset hash را ذخیره کند.
- نگاه به future candle ممنوع است.
- indicator/feature فقط از داده‌ای ساخته شود که در timestamp تصمیم واقعاً در دسترس بوده.
- اجرای live و backtest باید یک تابع `generate_signal` مشترک داشته باشند.

## تست‌های اجباری Strategy

- deterministic replay: ورودی یکسان → خروجی یکسان.
- no look-ahead.
- boundary cases برای insufficient candles.
- NaN/missing data policy.
- timezone consistency (UTC).
- property tests برای عدم تولید signal نامعتبر.
