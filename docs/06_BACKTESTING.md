# 06 — Backtesting & Validation

## اصل طلایی

Backtest باید همان `Strategy` و تا حد ممکن همان `Risk Engine` مورد استفاده در Paper/Live را اجرا کند. هیچ منطق استراتژی موازی مخصوص بک‌تست ساخته نشود.

## Pipeline

```text
Historical Parquet
→ Market Simulator
→ Strategy.generate_signal()
→ Risk Engine
→ Simulated Execution
→ Portfolio
→ Metrics
```

## شبیه‌سازی اجرای واقعی

حداقل موارد زیر لحاظ شوند:

- maker/taker fees
- configurable slippage
- spread assumptions
- funding برای perpetuals
- exchange quantity/price precision
- min notional
- gap behavior
- ambiguous candle rule

اگر در یک OHLC candle ترتیب برخورد stop/target معلوم نیست، نتیجه نباید خوش‌بینانه فرض شود؛ policy باید deterministic و ثبت‌شده باشد.

## جلوگیری از خطاهای پژوهشی

- look-ahead bias ممنوع
- survivorship bias بررسی شود
- timezone UTC
- feature availability بر اساس timestamp واقعی
- train/test leakage ممنوع
- parameter search و final evaluation جدا باشند

## Validation مراحل

1. Unit tests روی indicator/feature/strategy.
2. In-sample research.
3. Out-of-sample holdout.
4. Walk-forward evaluation.
5. Sensitivity analysis روی parameterها.
6. Paper trading.
7. Testnet/SEMI.
8. Live با risk محدود.

## Metrics

هیچ metric منفرد معیار قبولی نیست. حداقل:

- total return
- CAGR در صورت بازه کافی
- max drawdown
- profit factor
- expectancy per trade
- win rate
- average win/loss
- exposure/time in market
- turnover
- fee/funding/slippage costs
- Sharpe/Sortino با تعریف sampling ذخیره‌شده
- number of trades

## Promotion Gate اولیه

Strategy فقط وقتی از Research به Paper منتقل می‌شود که:

- تست‌ها سبز باشند؛
- OOS مثبت و معقول باشد؛
- performance فقط روی یک parameter نقطه‌ای نباشد؛
- بعد از fee/slippage هنوز expectancy مثبت باشد؛
- drawdown در risk budget تعریف‌شده قرار بگیرد؛
- تعداد معاملات برای نتیجه‌گیری بسیار کم نباشد.

Promotion به FULL هیچ‌وقت خودکار نیست.
