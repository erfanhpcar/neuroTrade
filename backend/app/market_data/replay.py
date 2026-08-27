"""In-memory MarketDataProvider for tests and later local replay.

Loads a frozen OHLCV series from Python objects or a JSON fixture. Performs no
network I/O and does not use HTTP clients, CCXT, or wall-clock time.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.domain.fields import require_symbol, require_timeframe
from app.domain.market import MarketSnapshot, OhlcvBar
from app.domain.timestamps import require_utc
from app.market_data.base import OhlcvSeries
from app.market_data.errors import (
    InsufficientMarketHistory,
    InvalidMarketDataRange,
    MarketDataError,
    UnknownMarketSeries,
)


def _parse_open_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise MarketDataError("bar open_time must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MarketDataError(f"bar open_time is not ISO-8601: {value!r}") from exc
    return require_utc(parsed, field="open_time")


def _parse_bar(raw: object) -> OhlcvBar:
    if not isinstance(raw, dict):
        raise MarketDataError(f"bar must be an object, got {type(raw).__name__}")
    required = ("open_time", "open", "high", "low", "close", "volume")
    missing = [key for key in required if key not in raw]
    if missing:
        raise MarketDataError(f"bar is missing fields: {', '.join(missing)}")
    unexpected = sorted(set(raw) - set(required))
    if unexpected:
        raise MarketDataError(f"bar has unexpected fields: {', '.join(unexpected)}")
    return OhlcvBar(
        open_time=_parse_open_time(raw["open_time"]),
        open=raw["open"],
        high=raw["high"],
        low=raw["low"],
        close=raw["close"],
        volume=raw["volume"],
    )


def series_from_json_payload(payload: object) -> OhlcvSeries:
    """Build an ``OhlcvSeries`` from a decoded fixture object."""

    if not isinstance(payload, dict):
        raise MarketDataError(f"replay payload must be an object, got {type(payload).__name__}")
    required = ("provider", "symbol", "timeframe", "bars")
    missing = [key for key in required if key not in payload]
    if missing:
        raise MarketDataError(f"replay payload is missing fields: {', '.join(missing)}")
    allowed = set(required) | {"dataset_hash"}
    unexpected = sorted(set(payload) - allowed)
    if unexpected:
        raise MarketDataError(f"replay payload has unexpected fields: {', '.join(unexpected)}")

    bars_raw = payload["bars"]
    if not isinstance(bars_raw, list):
        raise MarketDataError("replay payload bars must be a list")

    provider = payload["provider"]
    symbol = payload["symbol"]
    timeframe = payload["timeframe"]
    if not isinstance(provider, str):
        raise MarketDataError("provider must be a string")
    if not isinstance(symbol, str):
        raise MarketDataError("symbol must be a string")
    if not isinstance(timeframe, str):
        raise MarketDataError("timeframe must be a string")

    dataset_hash = payload.get("dataset_hash")
    if dataset_hash is not None and not isinstance(dataset_hash, str):
        raise MarketDataError("dataset_hash must be a string when provided")

    return OhlcvSeries.from_bars(
        provider=provider,
        symbol=symbol,
        timeframe=timeframe,
        bars=tuple(_parse_bar(item) for item in bars_raw),
        dataset_hash=dataset_hash,
    )


def load_series_from_json_path(path: Path) -> OhlcvSeries:
    """Load a replay series from a UTF-8 JSON file. Does not fetch URLs."""

    if not isinstance(path, Path):
        raise TypeError("path must be pathlib.Path")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MarketDataError(f"unable to read replay fixture {path}") from exc
    try:
        payload: object = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MarketDataError(f"replay fixture {path} is not valid JSON") from exc
    return series_from_json_payload(payload)


class ReplayMarketDataProvider:
    """Fixture-backed provider. ``name`` is always ``replay``."""

    def __init__(self, *series: OhlcvSeries) -> None:
        if not series:
            raise MarketDataError("ReplayMarketDataProvider requires at least one OhlcvSeries")
        keyed: dict[tuple[str, str], OhlcvSeries] = {}
        for item in series:
            if not isinstance(item, OhlcvSeries):
                raise TypeError(f"expected OhlcvSeries, got {type(item).__name__}")
            key = (item.symbol, item.timeframe)
            if key in keyed:
                raise MarketDataError(f"duplicate replay series for {item.symbol} {item.timeframe}")
            keyed[key] = item
        self._series = keyed

    @classmethod
    def from_json_path(cls, path: Path) -> ReplayMarketDataProvider:
        return cls(load_series_from_json_path(path))

    @property
    def name(self) -> str:
        return "replay"

    def _require_series(self, symbol: str, timeframe: str) -> OhlcvSeries:
        key = (require_symbol(symbol), require_timeframe(timeframe))
        try:
            return self._series[key]
        except KeyError as exc:
            raise UnknownMarketSeries(
                f"no replay series for symbol={key[0]!r} timeframe={key[1]!r}"
            ) from exc

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
        source = self._require_series(symbol, timeframe)
        filtered = tuple(bar for bar in source.bars if start_utc <= bar.open_time <= end_utc)
        return OhlcvSeries(
            provider=source.provider,
            symbol=source.symbol,
            timeframe=source.timeframe,
            bars=filtered,
            dataset_hash=source.dataset_hash,
        )

    async def latest_snapshot(
        self,
        symbol: str,
        timeframe: str,
        *,
        timestamp: datetime,
    ) -> MarketSnapshot:
        as_of = require_utc(timestamp, field="timestamp")
        source = self._require_series(symbol, timeframe)
        eligible = tuple(bar for bar in source.bars if bar.open_time <= as_of)
        if not eligible:
            raise InsufficientMarketHistory(
                f"no bar at or before {as_of.isoformat()} for {source.symbol} {source.timeframe}"
            )
        return MarketSnapshot(
            symbol=source.symbol,
            timeframe=source.timeframe,
            timestamp=as_of,
            bar=eligible[-1],
            provider=source.provider,
            dataset_hash=source.dataset_hash,
        )
