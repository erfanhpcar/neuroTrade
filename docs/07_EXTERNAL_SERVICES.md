# 07 — External Services & Exchange Adapters

## Market Data

V0/V1 باید تا حد ممکن از Public Market Data رایگان استفاده کند.

### Providerهای اولیه

- Bybit public REST/WebSocket
- Binance public REST/WebSocket

برای OHLCV/ticker/public order book معمولاً API key لازم نیست. Provider interface باید مستقل از Strategy باشد.

```python
class MarketDataProvider(Protocol):
    async def fetch_ohlcv(...): ...
    async def stream_ticker(...): ...
```

## Execution Adapter

```python
class ExecutionAdapter(Protocol):
    async def get_balance(...): ...
    async def get_positions(...): ...
    async def submit_order(...): ...
    async def cancel_order(...): ...
    async def get_open_orders(...): ...
```

### CCXT

اگر exchange موردنظر توسط CCXT به شکل کافی پشتیبانی شود، استفاده از CCXT مجاز است. در غیر این صورت native adapter نوشته می‌شود. هیچ کد Strategy نباید به CCXT وابسته باشد.

## The True Trade

The True Trade در UI حساب قابلیت ساخت API Key با permissionهای زیر نشان می‌دهد:

- Readonly
- Futures Trading
- Transfer
- Withdrawal
- Allowed IP addresses

برای neuroTrade در صورت استفاده live:

- `Readonly`: فعال
- `Futures Trading`: فقط در فاز SEMI/LIVE فعال
- `Transfer`: غیرفعال
- `Withdrawal`: **همیشه غیرفعال**
- IP whitelist: IP ثابت سرور production

قبل از پیاده‌سازی `TrueTradeExecutionAdapter` باید مستندات رسمی endpoint/auth/signature/rate-limit و Demo/Test environment اعتبارسنجی شود. تا آن زمان TTT یک planned adapter است، نه dependency هسته.

## Secrets

- `.env` و secret manager؛ هرگز Git.
- secret در frontend ممنوع.
- key rotation procedure مستند شود.
- permission حداقلی.

## Error policy

برای submit order retry کور ممنوع است. پس از timeout ابتدا با `client_order_id` و reconciliation بررسی شود که سفارش قبلاً ایجاد نشده باشد. Retry فقط idempotent/safe باشد.
