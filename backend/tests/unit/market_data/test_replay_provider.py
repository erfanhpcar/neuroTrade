import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.errors import InvalidFinancialValue, InvalidTimestamp
from app.domain.market import MarketSnapshot, OhlcvBar
from app.market_data.base import MarketDataProvider, OhlcvSeries, hash_ohlcv_bars, normalize_bars
from app.market_data.errors import (
    ConflictingDuplicateBars,
    InsufficientMarketHistory,
    InvalidMarketDataRange,
    MarketDataError,
    UnknownMarketSeries,
)
from app.market_data.replay import ReplayMarketDataProvider, series_from_json_payload

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "replay" / "btc_usdt_4h.json"


def _utc(hour: int, day: int = 1) -> datetime:
    return datetime(2026, 8, day, hour, 0, tzinfo=UTC)


def _bar(
    hour: int,
    *,
    close: str = "65100.50",
    volume: str = "1.0",
    day: int = 1,
) -> OhlcvBar:
    open_price = Decimal("65000.00")
    close_price = Decimal(close)
    high = max(open_price, close_price) + Decimal("200")
    low = min(open_price, close_price) - Decimal("100")
    return OhlcvBar(
        open_time=_utc(hour, day=day),
        open=open_price,
        high=high,
        low=low,
        close=close_price,
        volume=Decimal(volume),
    )


def test_replay_provider_satisfies_protocol() -> None:
    provider = ReplayMarketDataProvider.from_json_path(FIXTURE_PATH)
    assert isinstance(provider, MarketDataProvider)
    assert provider.name == "replay"


def test_json_fixture_round_trip_is_deterministic() -> None:
    first = ReplayMarketDataProvider.from_json_path(FIXTURE_PATH)
    second = ReplayMarketDataProvider.from_json_path(FIXTURE_PATH)
    series_a = asyncio.run(
        first.fetch_ohlcv(
            "BTC/USDT",
            "4h",
            start=_utc(0),
            end=_utc(20),
        )
    )
    series_b = asyncio.run(
        second.fetch_ohlcv(
            "BTC/USDT",
            "4h",
            start=_utc(0),
            end=_utc(20),
        )
    )
    assert series_a.bars == series_b.bars
    assert series_a.dataset_hash == series_b.dataset_hash
    assert len(series_a.bars) == 6
    assert series_a.dataset_hash == hash_ohlcv_bars(
        provider="replay",
        symbol="BTC/USDT",
        timeframe="4h",
        bars=series_a.bars,
    )


def test_fetch_ohlcv_inclusive_range_excludes_outside_bars() -> None:
    provider = ReplayMarketDataProvider.from_json_path(FIXTURE_PATH)
    series = asyncio.run(
        provider.fetch_ohlcv(
            "BTC/USDT",
            "4h",
            start=_utc(4),
            end=_utc(12),
        )
    )
    assert [bar.open_time for bar in series.bars] == [_utc(4), _utc(8), _utc(12)]
    assert (
        series.dataset_hash
        == asyncio.run(
            provider.fetch_ohlcv("BTC/USDT", "4h", start=_utc(0), end=_utc(20))
        ).dataset_hash
    )


def test_fetch_ohlcv_empty_window_returns_empty_series() -> None:
    provider = ReplayMarketDataProvider.from_json_path(FIXTURE_PATH)
    series = asyncio.run(
        provider.fetch_ohlcv(
            "BTC/USDT",
            "4h",
            start=_utc(1),
            end=_utc(2),
        )
    )
    assert series.bars == ()
    assert series.symbol == "BTC/USDT"


def test_fetch_ohlcv_rejects_inverted_range() -> None:
    provider = ReplayMarketDataProvider.from_json_path(FIXTURE_PATH)
    with pytest.raises(InvalidMarketDataRange, match="after end"):
        asyncio.run(
            provider.fetch_ohlcv(
                "BTC/USDT",
                "4h",
                start=_utc(12),
                end=_utc(4),
            )
        )


def test_fetch_ohlcv_rejects_naive_bounds() -> None:
    provider = ReplayMarketDataProvider.from_json_path(FIXTURE_PATH)
    with pytest.raises(InvalidTimestamp, match="naive"):
        asyncio.run(
            provider.fetch_ohlcv(
                "BTC/USDT",
                "4h",
                start=datetime(2026, 8, 1, 0, 0),
                end=_utc(4),
            )
        )


def test_unknown_symbol_or_timeframe_is_rejected() -> None:
    provider = ReplayMarketDataProvider.from_json_path(FIXTURE_PATH)
    with pytest.raises(UnknownMarketSeries, match="ETH/USDT"):
        asyncio.run(
            provider.fetch_ohlcv(
                "ETH/USDT",
                "4h",
                start=_utc(0),
                end=_utc(4),
            )
        )
    with pytest.raises(UnknownMarketSeries, match="1h"):
        asyncio.run(provider.latest_snapshot("BTC/USDT", "1h", timestamp=_utc(4)))


def test_latest_snapshot_uses_last_bar_at_or_before_timestamp() -> None:
    provider = ReplayMarketDataProvider.from_json_path(FIXTURE_PATH)
    snapshot = asyncio.run(
        provider.latest_snapshot(
            "BTC/USDT",
            "4h",
            timestamp=_utc(10),
        )
    )
    assert isinstance(snapshot, MarketSnapshot)
    assert snapshot.bar.open_time == _utc(8)
    assert snapshot.bar.open_time <= snapshot.timestamp
    assert snapshot.provider == "replay"
    assert snapshot.dataset_hash is not None


def test_latest_snapshot_does_not_use_future_bar() -> None:
    provider = ReplayMarketDataProvider.from_json_path(FIXTURE_PATH)
    snapshot = asyncio.run(
        provider.latest_snapshot(
            "BTC/USDT",
            "4h",
            timestamp=_utc(4),
        )
    )
    assert snapshot.bar.open_time == _utc(4)
    later = asyncio.run(provider.fetch_ohlcv("BTC/USDT", "4h", start=_utc(8), end=_utc(8)))
    assert later.bars[0].open_time > snapshot.timestamp
    assert snapshot.bar.open_time < later.bars[0].open_time


def test_latest_snapshot_before_first_bar_is_insufficient() -> None:
    provider = ReplayMarketDataProvider.from_json_path(FIXTURE_PATH)
    with pytest.raises(InsufficientMarketHistory, match="no bar"):
        asyncio.run(
            provider.latest_snapshot(
                "BTC/USDT",
                "4h",
                timestamp=_utc(0) - timedelta(hours=1),
            )
        )


def test_ohlcv_values_are_decimal_not_float() -> None:
    provider = ReplayMarketDataProvider.from_json_path(FIXTURE_PATH)
    series = asyncio.run(provider.fetch_ohlcv("BTC/USDT", "4h", start=_utc(0), end=_utc(0)))
    bar = series.bars[0]
    assert type(bar.close) is Decimal
    assert type(bar.volume) is Decimal
    assert not isinstance(bar.close, float)


def test_normalize_collapses_identical_duplicates() -> None:
    bar = _bar(0)
    normalized = normalize_bars((bar, bar, _bar(4, close="65020.00")))
    assert normalized == (bar, _bar(4, close="65020.00"))


def test_normalize_rejects_conflicting_duplicates() -> None:
    with pytest.raises(ConflictingDuplicateBars, match="conflicting"):
        normalize_bars((_bar(0, close="65100.50"), _bar(0, close="64000.00")))


def test_normalize_sorts_out_of_order_bars() -> None:
    first = _bar(0)
    second = _bar(4, close="65020.00")
    normalized = normalize_bars((second, first))
    assert normalized[0].open_time < normalized[1].open_time


def test_json_payload_rejects_binary_float_prices() -> None:
    payload = {
        "provider": "replay",
        "symbol": "BTC/USDT",
        "timeframe": "4h",
        "bars": [
            {
                "open_time": "2026-08-01T00:00:00+00:00",
                "open": 65000.1,
                "high": "65200.00",
                "low": "64900.00",
                "close": "65100.00",
                "volume": "1.0",
            }
        ],
    }
    with pytest.raises(InvalidFinancialValue, match="binary float"):
        series_from_json_payload(payload)


def test_json_payload_rejects_naive_open_time() -> None:
    payload = {
        "provider": "replay",
        "symbol": "BTC/USDT",
        "timeframe": "4h",
        "bars": [
            {
                "open_time": "2026-08-01T00:00:00",
                "open": "65000.00",
                "high": "65200.00",
                "low": "64900.00",
                "close": "65100.00",
                "volume": "1.0",
            }
        ],
    }
    with pytest.raises(InvalidTimestamp, match="naive"):
        series_from_json_payload(payload)


def test_empty_provider_is_rejected() -> None:
    with pytest.raises(MarketDataError, match="at least one"):
        ReplayMarketDataProvider()


def test_duplicate_series_keys_are_rejected() -> None:
    series = OhlcvSeries.from_bars(
        provider="replay",
        symbol="BTC/USDT",
        timeframe="4h",
        bars=(_bar(0),),
    )
    with pytest.raises(MarketDataError, match="duplicate replay series"):
        ReplayMarketDataProvider(series, series)
