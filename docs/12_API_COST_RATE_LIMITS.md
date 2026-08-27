# 12 — API Cost & Rate Limits

## اصل هزینه MVP

V0/V1 باید بتواند با هزینه API تقریباً صفر اجرا شود.

## Public Market Data

برای داده‌های عمومی بازار، providerهای اصلی Bybit/Binance هستند. Public REST/WebSocket معمولاً برای OHLCV، ticker، trades و order book نیاز به account API key ندارند.

## REST vs WebSocket policy

- Historical backfill: REST
- Live ticker/trades/candles: WebSocket
- REST polling فقط برای recovery/periodic reconciliation
- reconnect با exponential backoff + jitter
- snapshot + delta stream در صورت استفاده order book

## Rate limiting

Rate limit نباید با یک عدد hardcoded عمومی مدل شود. هر provider adapter باید:

- limitهای رسمی همان exchange را config کند؛
- 429/ban response را log کند؛
- exponential backoff داشته باشد؛
- queue/budget per endpoint داشته باشد؛
- درخواست duplicate غیرضروری را cache/coalesce کند.

## Private Trading API

API key فقط در فاز execution لازم است. هزینه مستقیم API معمولاً جدا از trading fee نیست، اما fee/funding/slippage باید جزو economics strategy باشند.

## Paid data

در MVP data vendor پولی لازم نیست. فقط اگر research نشان داد نیاز به tick history عمیق، latency پایین، consolidated institutional feed یا long-range order-book history داریم، vendor پولی ارزیابی می‌شود.

## AI cost

در MVP = `0`. اگر AI extension فعال شد، هزینه آن باید per experiment/trade ثبت و در A/B evaluation لحاظ شود.
