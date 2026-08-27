"""Bybit public REST OHLCV adapter.

Uses official GET /v5/market/kline. No API keys, no CCXT, no private endpoints.
HTTP lives only in this venue adapter. Contract modules stay HTTP-free.

Docs: https://bybit-exchange.github.io/docs/v5/market/kline
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Final

import httpx

from app.domain.fields import require_symbol, require_text, require_timeframe
from app.domain.market import MarketSnapshot, OhlcvBar
from app.domain.timestamps import require_utc
from app.market_data.base import OhlcvSeries
from app.market_data.errors import (
    InsufficientMarketHistory,
    InvalidMarketDataRange,
    MarketDataError,
    MarketDataHttpError,
    MarketDataRateLimited,
    UnsupportedMarketCategory,
    UnsupportedTimeframe,
)
from app.market_data.rate_limit import (
    DEFAULT_BYBIT_KLINE_BUDGET,
    RateLimitBudget,
    SlidingWindowRateLimiter,
    UnitIntervalRng,
    backoff_seconds,
    default_rng,
)

logger = logging.getLogger("neurotrade.market_data.bybit")

BYBIT_KLINE_PATH: Final = "/v5/market/kline"
BYBIT_DEFAULT_BASE_URL: Final = "https://api.bybit.com"
BYBIT_PAGE_LIMIT: Final = 1000
BYBIT_MAX_PAGES: Final = 50
BYBIT_SUCCESS_RET_CODE: Final = 0
BYBIT_TOO_MANY_VISITS_RET_CODE: Final = 10006
BYBIT_CATEGORIES: Final = frozenset({"spot", "linear", "inverse"})

# neuroTrade timeframes -> Bybit interval enum.
# https://bybit-exchange.github.io/docs/v5/market/kline
BYBIT_INTERVAL_BY_TIMEFRAME: Final[dict[str, str]] = {
    "1m": "1",
    "3m": "3",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "2h": "120",
    "4h": "240",
    "6h": "360",
    "12h": "720",
    "1d": "D",
    "1w": "W",
    "1M": "M",
}

_AUTH_HEADER_NAMES: Final = frozenset(
    {
        "authorization",
        "x-api-key",
        "x-bapi-api-key",
        "x-bapi-sign",
        "x-bapi-timestamp",
        "x-bapi-recv-window",
    }
)


def to_bybit_symbol(symbol: str) -> str:
    """Map ``BTC/USDT`` (or already-concatenated ``BTCUSDT``) to Bybit uppercase."""

    text = require_symbol(symbol)
    if "/" in text:
        parts = text.split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise MarketDataError(f"symbol {symbol!r} must look like BASE/QUOTE")
        text = f"{parts[0]}{parts[1]}"
    if not text.isalnum() or text != text.upper():
        raise MarketDataError("Bybit symbol must be uppercase alphanumeric")
    return text


def to_bybit_interval(timeframe: str) -> str:
    """Map a neuroTrade timeframe to the official Bybit kline interval."""

    key = require_timeframe(timeframe)
    try:
        return BYBIT_INTERVAL_BY_TIMEFRAME[key]
    except KeyError as exc:
        raise UnsupportedTimeframe(
            f"timeframe {key!r} has no Bybit kline interval mapping"
        ) from exc


def to_bybit_category(category: str) -> str:
    text = require_text(category, field="category")
    if text not in BYBIT_CATEGORIES:
        raise UnsupportedMarketCategory(
            f"category {text!r} is not a Bybit kline category; "
            f"use one of {sorted(BYBIT_CATEGORIES)}"
        )
    return text


def create_bybit_http_client(
    *,
    base_url: str = BYBIT_DEFAULT_BASE_URL,
    timeout_seconds: float = 10.0,
) -> httpx.AsyncClient:
    """Public client. Callers own close(). Never attach exchange API keys."""

    return httpx.AsyncClient(
        base_url=base_url,
        timeout=timeout_seconds,
        follow_redirects=False,
        headers={"User-Agent": "neurotrade-market-data/0.1"},
    )


class BybitPublicRestProvider:
    """``MarketDataProvider`` over Bybit public REST klines.

    Always sends ``category`` so Bybit cannot silently default the request to
    ``linear``. Default category is ``spot`` for ``BTC/USDT`` cash history.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        category: str = "spot",
        rate_limiter: SlidingWindowRateLimiter | None = None,
        page_limit: int = BYBIT_PAGE_LIMIT,
        max_pages: int = BYBIT_MAX_PAGES,
        rng: UnitIntervalRng | None = None,
    ) -> None:
        if not isinstance(client, httpx.AsyncClient):
            raise TypeError("client must be httpx.AsyncClient")
        if page_limit < 1 or page_limit > BYBIT_PAGE_LIMIT:
            raise MarketDataError(f"page_limit must be in 1..{BYBIT_PAGE_LIMIT}")
        if max_pages < 1:
            raise MarketDataError("max_pages must be >= 1")
        self._client = client
        self._category = to_bybit_category(category)
        self._rate_limiter = rate_limiter or SlidingWindowRateLimiter(DEFAULT_BYBIT_KLINE_BUDGET)
        self._page_limit = page_limit
        self._max_pages = max_pages
        self._rng: UnitIntervalRng = rng or default_rng()

    @property
    def name(self) -> str:
        return "bybit"

    @property
    def category(self) -> str:
        return self._category

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        *,
        start: datetime,
        end: datetime,
    ) -> OhlcvSeries:
        start_utc = require_utc(start, field="start")
        end_utc = require_utc(end, field="end")
        if start_utc > end_utc:
            raise InvalidMarketDataRange(
                f"start {start_utc.isoformat()} is after end {end_utc.isoformat()}"
            )
        venue_symbol = to_bybit_symbol(symbol)
        interval = to_bybit_interval(timeframe)
        canonical_symbol = require_symbol(symbol)
        canonical_timeframe = require_timeframe(timeframe)

        collected: list[OhlcvBar] = []
        page_end = end_utc
        previous_oldest_ms: int | None = None
        for _page in range(self._max_pages):
            raw_list = await self._get_kline_list(
                venue_symbol=venue_symbol,
                interval=interval,
                start_ms=_to_millis(start_utc),
                end_ms=_to_millis(page_end),
                limit=self._page_limit,
            )
            if not raw_list:
                break
            page_bars = tuple(_parse_kline_row(row) for row in raw_list)
            collected.extend(page_bars)
            oldest = min(bar.open_time for bar in page_bars)
            oldest_ms = _to_millis(oldest)
            if previous_oldest_ms is not None and oldest_ms >= previous_oldest_ms:
                raise MarketDataHttpError("Bybit kline pagination did not move backward")
            previous_oldest_ms = oldest_ms
            if len(raw_list) < self._page_limit or oldest <= start_utc:
                break
            page_end = datetime.fromtimestamp((oldest_ms - 1) / 1000, tz=UTC)
            if page_end < start_utc:
                break
        else:
            raise MarketDataHttpError(
                f"Bybit kline pagination exceeded max_pages={self._max_pages}"
            )

        filtered = tuple(bar for bar in collected if start_utc <= bar.open_time <= end_utc)
        return OhlcvSeries.from_bars(
            provider=self.name,
            symbol=canonical_symbol,
            timeframe=canonical_timeframe,
            bars=filtered,
        )

    async def latest_snapshot(
        self,
        symbol: str,
        timeframe: str,
        *,
        timestamp: datetime,
    ) -> MarketSnapshot:
        as_of = require_utc(timestamp, field="timestamp")
        venue_symbol = to_bybit_symbol(symbol)
        interval = to_bybit_interval(timeframe)
        raw_list = await self._get_kline_list(
            venue_symbol=venue_symbol,
            interval=interval,
            start_ms=None,
            end_ms=_to_millis(as_of),
            limit=2,
        )
        bars = tuple(_parse_kline_row(row) for row in raw_list)
        eligible = tuple(bar for bar in bars if bar.open_time <= as_of)
        if not eligible:
            raise InsufficientMarketHistory(
                f"no bar at or before {as_of.isoformat()} for {require_symbol(symbol)} "
                f"{require_timeframe(timeframe)}"
            )
        series = OhlcvSeries.from_bars(
            provider=self.name,
            symbol=require_symbol(symbol),
            timeframe=require_timeframe(timeframe),
            bars=eligible,
        )
        return MarketSnapshot(
            symbol=series.symbol,
            timeframe=series.timeframe,
            timestamp=as_of,
            bar=series.bars[-1],
            provider=series.provider,
            dataset_hash=series.dataset_hash,
        )

    async def _get_kline_list(
        self,
        *,
        venue_symbol: str,
        interval: str,
        start_ms: int | None,
        end_ms: int,
        limit: int,
    ) -> list[object]:
        params: dict[str, str] = {
            "category": self._category,
            "symbol": venue_symbol,
            "interval": interval,
            "end": str(end_ms),
            "limit": str(limit),
        }
        if start_ms is not None:
            params["start"] = str(start_ms)

        budget = self._rate_limiter.budget
        last_error: MarketDataHttpError | None = None
        attempts = budget.max_retries + 1
        for attempt in range(attempts):
            await self._rate_limiter.acquire()
            try:
                response = await self._client.get(BYBIT_KLINE_PATH, params=params)
            except httpx.TimeoutException as exc:
                last_error = MarketDataHttpError("Bybit kline request timed out")
                last_error.__cause__ = exc
                await self._sleep_backoff(attempt, budget)
                continue
            except httpx.RequestError as exc:
                last_error = MarketDataHttpError("Bybit kline request failed")
                last_error.__cause__ = exc
                await self._sleep_backoff(attempt, budget)
                continue

            _assert_no_auth_headers(response.request.headers)

            if _is_http_rate_limited(response):
                logger.warning(
                    "bybit GET %s rate-limited status=%s attempt=%s",
                    BYBIT_KLINE_PATH,
                    response.status_code,
                    attempt,
                )
                last_error = MarketDataRateLimited(
                    f"Bybit kline HTTP {response.status_code} rate limit"
                )
                retry_after = _retry_after_seconds(response, attempt, budget, self._rng)
                await self._rate_limiter.sleep(retry_after)
                continue

            if response.status_code >= 400:
                raise MarketDataHttpError(f"Bybit kline HTTP {response.status_code}")

            payload = _parse_json_object(response)
            ret_code = payload.get("retCode")
            ret_msg = payload.get("retMsg", "")
            if ret_code == BYBIT_TOO_MANY_VISITS_RET_CODE:
                logger.warning(
                    "bybit GET %s retCode=%s attempt=%s",
                    BYBIT_KLINE_PATH,
                    ret_code,
                    attempt,
                )
                last_error = MarketDataRateLimited(f"Bybit kline retCode={ret_code} {ret_msg!r}")
                await self._sleep_backoff(attempt, budget)
                continue
            if ret_code != BYBIT_SUCCESS_RET_CODE:
                raise MarketDataHttpError(f"Bybit kline retCode={ret_code} {ret_msg!r}")
            result = payload.get("result")
            if not isinstance(result, dict):
                raise MarketDataHttpError("Bybit kline result must be an object")
            raw_list = result.get("list")
            if raw_list is None:
                return []
            if not isinstance(raw_list, list):
                raise MarketDataHttpError("Bybit kline list must be an array")
            return raw_list

        if last_error is not None:
            raise last_error
        raise MarketDataHttpError("Bybit kline request failed without a captured error")

    async def _sleep_backoff(self, attempt: int, budget: RateLimitBudget) -> None:
        if attempt >= budget.max_retries:
            return
        delay = backoff_seconds(attempt, budget, self._rng)
        await self._rate_limiter.sleep(delay)


def _to_millis(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _from_millis(value: object) -> datetime:
    if isinstance(value, bool) or value is None:
        raise MarketDataError("kline startTime must be millisecond epoch")
    if isinstance(value, int):
        millis = value
    elif isinstance(value, str):
        text = value.strip()
        if not text.isdigit():
            raise MarketDataError(f"kline startTime is not millisecond epoch: {value!r}")
        millis = int(text)
    else:
        raise MarketDataError(f"kline startTime must be str or int, got {type(value).__name__}")
    if millis < 0:
        raise MarketDataError("kline startTime must be >= 0")
    return datetime.fromtimestamp(millis / 1000, tz=UTC)


def _parse_kline_row(row: object) -> OhlcvBar:
    if not isinstance(row, list) or len(row) < 6:
        raise MarketDataError("Bybit kline row must be an array of at least 6 values")
    return OhlcvBar(
        open_time=_from_millis(row[0]),
        open=row[1],
        high=row[2],
        low=row[3],
        close=row[4],
        volume=row[5],
    )


def _parse_json_object(response: httpx.Response) -> dict[str, object]:
    try:
        payload: object = response.json()
    except ValueError as exc:
        raise MarketDataHttpError("Bybit kline response is not JSON") from exc
    if not isinstance(payload, dict):
        raise MarketDataHttpError("Bybit kline JSON body must be an object")
    return payload


def _is_http_rate_limited(response: httpx.Response) -> bool:
    if response.status_code == 429:
        return True
    if response.status_code != 403:
        return False
    body = response.text.lower()
    return "access too frequent" in body or "too many visits" in body


def _retry_after_seconds(
    response: httpx.Response,
    attempt: int,
    budget: RateLimitBudget,
    rng: UnitIntervalRng,
) -> float:
    header = response.headers.get("Retry-After")
    if header is not None:
        try:
            parsed = float(header)
        except ValueError:
            parsed = None
        if parsed is not None and parsed >= 0:
            return min(parsed, budget.max_backoff_seconds)
    return backoff_seconds(attempt, budget, rng)


def _assert_no_auth_headers(headers: Mapping[str, str]) -> None:
    for name in headers:
        if name.lower() in _AUTH_HEADER_NAMES:
            raise MarketDataHttpError(
                "Bybit public kline request must not include exchange auth headers"
            )
