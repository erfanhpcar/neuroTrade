# 07 — External Services & Exchange Adapters

## اصل

هسته neuroTrade به provider خاص وابسته نیست. Market Data و Execution از طریق interface/adapter جدا می‌شوند.

هر Coding Agent قبل از اضافه‌کردن provider/exchange جدید باید `AGENTS.md`, `backend/AGENTS.md`, `16_CODING_AGENT_GUIDELINES.md` و این سند را بخواند. اگر API رسمی، auth/signature یا sandbox behavior نامشخص است، agent حق ندارد برای سرمایه واقعی endpoint خصوصی/undocumented را حدس بزند یا reverse-engineer کند.

## Market Data — V0/V1

برای شروع از Public APIهای Bybit یا Binance استفاده می‌کنیم:

- ticker/price
- OHLCV
- trades
- order book در صورت نیاز
- funding/open interest در صورت نیاز به research

Public market data معمولاً بدون private API key قابل دریافت است. Historical data از REST و realtime از WebSocket گرفته می‌شود.

`MarketDataProvider` باید exchange-agnostic contract باشد.

Phase 2 interface (implemented; live venue adapters are later):

```python
class MarketDataProvider(Protocol):
    name: str

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        *,
        start: datetime,
        end: datetime,
    ) -> OhlcvSeries:
        ...

    async def latest_snapshot(
        self,
        symbol: str,
        timeframe: str,
        *,
        timestamp: datetime,
    ) -> MarketSnapshot:
        ...
```

Contract notes:

- No private API key. Public market data only.
- `fetch_ohlcv` returns closed bars with `open_time` in the inclusive UTC range `[start, end]`.
- Results are sorted by `open_time`. Identical duplicate bars collapse; conflicting duplicates raise.
- `latest_snapshot` uses the last bar with `open_time <= timestamp` and never a later bar.
- Prices/volume are `Decimal`. Naive timestamps are rejected.
- `ReplayMarketDataProvider` is the offline implementation for unit tests and later local replay. It loads JSON fixtures from disk and performs no network I/O.
- Live REST/WebSocket adapters (Bybit/Binance) are not part of this increment. Do not add CCXT until a public provider is implemented.
- Unit tests must not depend on the public internet.

## Execution

`ExecutionAdapter` contract مستقل است:

- fetch account/balance
- fetch open orders/positions/fills
- create/cancel order
- reconciliation identifiers
- exchange precision/limits

Paper adapter ابتدا پیاده می‌شود. Private exchange adapter فقط در Phase 9 و sandbox/demo.

## CCXT

CCXT یک abstraction/library است، نه data provider. اگر exchange موردنظر به شکل مناسب پشتیبانی شود می‌تواند implementation یک adapter باشد. نباید typeهای CCXT وارد Domain/Strategy شوند.

## The True Trade

از UI حساب مشخص است API Management حداقل permissionهای زیر را دارد:

- `Readonly`
- `Futures Trading`
- `Transfer`
- `Withdrawal`
- Allowed IP addresses

Policy neuroTrade:

```text
Readonly        enable فقط در صورت نیاز account/reconciliation
Futures Trading enable فقط برای Demo/Testnet/SEMI/Live تأییدشده
Transfer        disabled
Withdrawal      ALWAYS disabled
Allowed IP      IP سرور در محیط private/live در صورت پشتیبانی
```

قبل از نوشتن `TrueTradeExecutionAdapter` باید مستندات رسمی این موارد بررسی شود:

1. base URL و endpointها؛
2. authentication/signature/timestamp؛
3. symbol/contract metadata؛
4. create/cancel order؛
5. balance/open orders/positions/fills؛
6. client order id / idempotency support؛
7. rate limits؛
8. precision/min notional؛
9. error codes؛
10. Demo/Test API availability؛
11. WebSocket/private stream اگر موجود است.

تا زمانی که این contractها تأیید نشده‌اند، The True Trade فقط یک **planned adapter** است و Market Data می‌تواند مستقل از Bybit/Binance گرفته شود.

## Secrets

- هیچ secret واقعی در Git.
- backend env/secret manager فقط.
- private secret در frontend/`NEXT_PUBLIC_*` ممنوع.
- API keys در log ممنوع.
- `.env.example` فقط placeholder.

## Resilience

Read requestها می‌توانند retry محدود با exponential backoff/jitter داشته باشند.

برای order submission:

```text
submit
  ↓ timeout/unknown
DO NOT blind retry
  ↓
reconcile using client_order_id / open orders / fills
  ↓
known absent? → controlled retry
known present? → continue state
unknown? → HALT/alert
```

## Optional services later

CoinGecko برای universe metadata و News APIs/AI فقط در صورت نیاز research و پس از baseline اضافه می‌شوند؛ dependency اولیه نیستند.
