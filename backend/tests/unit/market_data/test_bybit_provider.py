import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest

from app.domain.errors import InvalidFinancialValue, InvalidTimestamp
from app.domain.market import MarketSnapshot
from app.market_data.base import MarketDataProvider, hash_ohlcv_bars
from app.market_data.bybit import (
    BYBIT_KLINE_PATH,
    BybitPublicRestProvider,
    to_bybit_category,
    to_bybit_interval,
    to_bybit_symbol,
)
from app.market_data.errors import (
    InsufficientMarketHistory,
    InvalidMarketDataRange,
    MarketDataError,
    MarketDataHttpError,
    MarketDataRateLimited,
    UnsupportedMarketCategory,
    UnsupportedTimeframe,
)
from app.market_data.integrity import inspect_series
from app.market_data.rate_limit import RateLimitBudget, SlidingWindowRateLimiter


class FakeClock:
    def __init__(self, start: float = 1_000.0) -> None:
        self.now = start
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _utc(hour: int, day: int = 1) -> datetime:
    return datetime(2026, 8, day, hour, 0, tzinfo=UTC)


def _ms(hour: int, day: int = 1) -> str:
    return str(int(_utc(hour, day=day).timestamp() * 1000))


def _row(hour: int, *, close: str = "65100.50", volume: str = "1.25", day: int = 1) -> list[str]:
    return [_ms(hour, day=day), "65000.00", "65300.00", "64900.00", close, volume, "81250.00"]


def _kline_json(rows: list[Any], *, ret_code: int = 0) -> dict[str, object]:
    return {
        "retCode": ret_code,
        "retMsg": "OK" if ret_code == 0 else "error",
        "result": {"symbol": "BTCUSDT", "category": "spot", "list": rows},
    }


def _unlimited_limiter(clock: FakeClock) -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter(
        RateLimitBudget(
            max_requests=1_000,
            window_seconds=1.0,
            max_retries=3,
            initial_backoff_seconds=0.5,
            max_backoff_seconds=8.0,
            jitter_ratio=0.0,
        ),
        clock=clock,
        sleeper=clock.sleep,
    )


class FakeBybit:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self._queue: list[httpx.Response] = []

    def queue_json(
        self,
        rows: list[Any],
        *,
        status: int = 200,
        ret_code: int = 0,
        retry_after: str | None = None,
    ) -> None:
        headers = {"Retry-After": retry_after} if retry_after is not None else {}
        self._queue.append(
            httpx.Response(status, json=_kline_json(rows, ret_code=ret_code), headers=headers)
        )

    def queue_text(self, status: int, text: str, *, retry_after: str | None = None) -> None:
        headers = {"Retry-After": retry_after} if retry_after is not None else {}
        self._queue.append(httpx.Response(status, text=text, headers=headers))

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if not self._queue:
            return httpx.Response(500, json=_kline_json([], ret_code=1))
        return self._queue.pop(0)


@asynccontextmanager
async def bybit_provider(
    fake: FakeBybit,
    **provider_kwargs: Any,
) -> AsyncIterator[tuple[BybitPublicRestProvider, FakeClock]]:
    transport = httpx.MockTransport(fake.handler)
    clock = FakeClock()
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://api.bybit.com",
        follow_redirects=False,
    ) as client:
        provider = BybitPublicRestProvider(
            client,
            category="spot",
            rate_limiter=_unlimited_limiter(clock),
            rng=lambda: 0.0,
            **provider_kwargs,
        )
        yield provider, clock


def test_symbol_and_interval_mapping() -> None:
    assert to_bybit_symbol("BTC/USDT") == "BTCUSDT"
    assert to_bybit_symbol("BTCUSDT") == "BTCUSDT"
    assert to_bybit_interval("4h") == "240"
    assert to_bybit_interval("1m") == "1"
    assert to_bybit_interval("1M") == "M"
    assert to_bybit_category("spot") == "spot"
    with pytest.raises(MarketDataError, match="uppercase"):
        to_bybit_symbol("btc/usdt")
    with pytest.raises(UnsupportedTimeframe, match="8h"):
        to_bybit_interval("8h")
    with pytest.raises(UnsupportedMarketCategory, match="option"):
        to_bybit_category("option")


def test_provider_satisfies_protocol() -> None:
    async def run() -> None:
        fake = FakeBybit()
        async with bybit_provider(fake) as (provider, _clock):
            assert isinstance(provider, MarketDataProvider)
            assert provider.name == "bybit"
            assert provider.category == "spot"

    asyncio.run(run())


def test_fetch_ohlcv_parses_reverse_list_to_chronological_decimals() -> None:
    fake = FakeBybit()
    fake.queue_json([_row(8), _row(4), _row(0)])

    async def run() -> None:
        async with bybit_provider(fake) as (provider, _clock):
            series = await provider.fetch_ohlcv("BTC/USDT", "4h", start=_utc(0), end=_utc(8))
        assert [bar.open_time for bar in series.bars] == [_utc(0), _utc(4), _utc(8)]
        assert type(series.bars[0].close) is Decimal
        assert series.bars[0].close == Decimal("65100.50")
        assert series.provider == "bybit"
        assert series.dataset_hash == hash_ohlcv_bars(
            provider="bybit",
            symbol="BTC/USDT",
            timeframe="4h",
            bars=series.bars,
        )
        request = fake.requests[0]
        assert request.url.path == BYBIT_KLINE_PATH
        assert request.url.params["category"] == "spot"
        assert request.url.params["symbol"] == "BTCUSDT"
        assert request.url.params["interval"] == "240"
        assert "x-bapi-api-key" not in {key.lower() for key in request.headers}
        report = inspect_series(series)
        assert report.has_issues is False
        assert report.input_was_unordered is False

    asyncio.run(run())


def test_gapped_kline_window_is_detected() -> None:
    fake = FakeBybit()
    fake.queue_json([_row(8), _row(0)])

    async def run() -> None:
        async with bybit_provider(fake) as (provider, _clock):
            series = await provider.fetch_ohlcv("BTC/USDT", "4h", start=_utc(0), end=_utc(8))
        report = inspect_series(series)
        assert [bar.open_time for bar in series.bars] == [_utc(0), _utc(8)]
        assert report.has_issues is True
        assert report.missing_open_times == (_utc(4),)

    asyncio.run(run())


def test_fetch_ohlcv_paginates_backward_until_start() -> None:
    fake = FakeBybit()
    fake.queue_json([_row(12), _row(8)])
    fake.queue_json([_row(8), _row(4)])
    fake.queue_json([_row(0)])

    async def run() -> None:
        async with bybit_provider(fake, page_limit=2) as (provider, _clock):
            series = await provider.fetch_ohlcv("BTC/USDT", "4h", start=_utc(0), end=_utc(12))
        assert [bar.open_time for bar in series.bars] == [_utc(0), _utc(4), _utc(8), _utc(12)]
        assert len(fake.requests) == 3
        first_end = int(fake.requests[0].url.params["end"])
        second_end = int(fake.requests[1].url.params["end"])
        assert second_end < first_end

    asyncio.run(run())


def test_fetch_ohlcv_inclusive_range_drops_outside_bars() -> None:
    fake = FakeBybit()
    fake.queue_json([_row(12), _row(8), _row(4), _row(0)])

    async def run() -> None:
        async with bybit_provider(fake) as (provider, _clock):
            series = await provider.fetch_ohlcv("BTC/USDT", "4h", start=_utc(4), end=_utc(8))
        assert [bar.open_time for bar in series.bars] == [_utc(4), _utc(8)]

    asyncio.run(run())


def test_fetch_ohlcv_empty_window_is_empty_series() -> None:
    fake = FakeBybit()
    fake.queue_json([])

    async def run() -> None:
        async with bybit_provider(fake) as (provider, _clock):
            series = await provider.fetch_ohlcv("BTC/USDT", "4h", start=_utc(1), end=_utc(2))
        assert series.bars == ()
        assert series.symbol == "BTC/USDT"

    asyncio.run(run())


def test_fetch_ohlcv_rejects_inverted_range_without_http() -> None:
    fake = FakeBybit()

    async def run() -> None:
        async with bybit_provider(fake) as (provider, _clock):
            with pytest.raises(InvalidMarketDataRange, match="after end"):
                await provider.fetch_ohlcv("BTC/USDT", "4h", start=_utc(8), end=_utc(0))
        assert fake.requests == []

    asyncio.run(run())


def test_fetch_ohlcv_rejects_naive_bounds() -> None:
    fake = FakeBybit()

    async def run() -> None:
        async with bybit_provider(fake) as (provider, _clock):
            with pytest.raises(InvalidTimestamp, match="naive"):
                await provider.fetch_ohlcv(
                    "BTC/USDT",
                    "4h",
                    start=datetime(2026, 8, 1, 0, 0),
                    end=_utc(4),
                )

    asyncio.run(run())


def test_conflicting_duplicates_across_pages_raise() -> None:
    fake = FakeBybit()
    fake.queue_json([_row(8, close="65100.50"), _row(4)])
    fake.queue_json([_row(4, close="65150.00"), _row(0)])

    async def run() -> None:
        async with bybit_provider(fake, page_limit=2) as (provider, _clock):
            with pytest.raises(MarketDataError, match="conflicting"):
                await provider.fetch_ohlcv("BTC/USDT", "4h", start=_utc(0), end=_utc(8))

    asyncio.run(run())


def test_binary_float_prices_are_rejected() -> None:
    fake = FakeBybit()
    fake.queue_json([[_ms(0), 65000.1, "65300.00", "64900.00", "65100.00", "1.0", "0"]])

    async def run() -> None:
        async with bybit_provider(fake) as (provider, _clock):
            with pytest.raises(InvalidFinancialValue, match="binary float"):
                await provider.fetch_ohlcv("BTC/USDT", "4h", start=_utc(0), end=_utc(0))

    asyncio.run(run())


def test_http_429_retries_then_succeeds() -> None:
    fake = FakeBybit()
    fake.queue_json([], status=429, retry_after="1")
    fake.queue_json([_row(0)])

    async def run() -> None:
        async with bybit_provider(fake) as (provider, clock):
            series = await provider.fetch_ohlcv("BTC/USDT", "4h", start=_utc(0), end=_utc(0))
        assert len(series.bars) == 1
        assert clock.sleeps == [1.0]
        assert len(fake.requests) == 2

    asyncio.run(run())


def test_retcode_10006_exhausted_retries_raise_rate_limited() -> None:
    fake = FakeBybit()
    for _ in range(4):
        fake.queue_json([], ret_code=10006)

    async def run() -> None:
        async with bybit_provider(fake) as (provider, clock):
            with pytest.raises(MarketDataRateLimited, match="10006"):
                await provider.fetch_ohlcv("BTC/USDT", "4h", start=_utc(0), end=_utc(0))
        assert len(fake.requests) == 4
        assert clock.sleeps == [0.5, 1.0, 2.0]

    asyncio.run(run())


def test_nonzero_retcode_is_not_retried() -> None:
    fake = FakeBybit()
    fake.queue_json([], ret_code=10001)

    async def run() -> None:
        async with bybit_provider(fake) as (provider, _clock):
            with pytest.raises(MarketDataHttpError, match="10001"):
                await provider.fetch_ohlcv("BTC/USDT", "4h", start=_utc(0), end=_utc(0))
        assert len(fake.requests) == 1

    asyncio.run(run())


def test_latest_snapshot_does_not_use_future_bar() -> None:
    fake = FakeBybit()
    fake.queue_json([_row(8), _row(4)])

    async def run() -> None:
        async with bybit_provider(fake) as (provider, _clock):
            snapshot = await provider.latest_snapshot("BTC/USDT", "4h", timestamp=_utc(4))
        assert isinstance(snapshot, MarketSnapshot)
        assert snapshot.bar.open_time == _utc(4)
        assert snapshot.bar.open_time <= snapshot.timestamp
        assert snapshot.provider == "bybit"
        params = fake.requests[0].url.params
        assert "start" not in params
        assert params["limit"] == "2"

    asyncio.run(run())


def test_latest_snapshot_before_history_is_insufficient() -> None:
    fake = FakeBybit()
    fake.queue_json([_row(4)])

    async def run() -> None:
        async with bybit_provider(fake) as (provider, _clock):
            with pytest.raises(InsufficientMarketHistory, match="no bar"):
                await provider.latest_snapshot(
                    "BTC/USDT",
                    "4h",
                    timestamp=_utc(0) - timedelta(hours=1),
                )

    asyncio.run(run())


def test_always_sends_category_query_param() -> None:
    fake = FakeBybit()
    fake.queue_json([_row(0)])

    async def run() -> None:
        async with bybit_provider(fake) as (provider, _clock):
            await provider.fetch_ohlcv("BTC/USDT", "4h", start=_utc(0), end=_utc(0))
        assert fake.requests[0].url.params["category"] == "spot"

    asyncio.run(run())
