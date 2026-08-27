import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from app.domain.market import OhlcvBar
from app.market_data.base import OhlcvSeries, normalize_bars
from app.market_data.errors import IncompleteOhlcvHistory, UnsupportedTimeframe
from app.market_data.integrity import (
    inspect_ohlcv,
    inspect_series,
    log_integrity_issues,
    require_contiguous_ohlcv,
)
from app.market_data.replay import ReplayMarketDataProvider
from app.market_data.timeframe import (
    timeframe_duration,
    timeframe_duration_seconds,
    uses_epoch_alignment,
)

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "replay" / "btc_usdt_4h.json"


def _utc(hour: int, day: int = 1, minute: int = 0) -> datetime:
    return datetime(2026, 8, day, hour, minute, tzinfo=UTC)


def _bar(open_time: datetime, *, close: str = "65100.50") -> OhlcvBar:
    open_price = Decimal("65000.00")
    close_price = Decimal(close)
    high = max(open_price, close_price) + Decimal("200")
    low = min(open_price, close_price) - Decimal("100")
    return OhlcvBar(
        open_time=open_time,
        open=open_price,
        high=high,
        low=low,
        close=close_price,
        volume=Decimal("1.0"),
    )


def test_timeframe_duration_covers_fixed_intervals() -> None:
    assert timeframe_duration("1m") == timedelta(minutes=1)
    assert timeframe_duration("4h") == timedelta(hours=4)
    assert timeframe_duration("1d") == timedelta(days=1)
    assert timeframe_duration("1w") == timedelta(days=7)
    assert timeframe_duration_seconds("4h") == 14_400
    assert uses_epoch_alignment("4h") is True
    assert uses_epoch_alignment("1w") is False


def test_calendar_month_has_no_fixed_duration() -> None:
    with pytest.raises(UnsupportedTimeframe, match="1M"):
        timeframe_duration("1M")
    with pytest.raises(UnsupportedTimeframe, match="8h"):
        inspect_ohlcv((), "8h")


def test_contiguous_4h_series_has_no_issues() -> None:
    bars = (_bar(_utc(0)), _bar(_utc(4), close="65020.00"), _bar(_utc(8), close="65410.00"))
    report = inspect_ohlcv(bars, "4h")
    assert report.has_issues is False
    assert report.is_contiguous is True
    assert report.is_epoch_aligned is True
    assert report.input_was_unordered is False
    assert report.bar_count == 3
    assert require_contiguous_ohlcv(
        OhlcvSeries.from_bars(provider="replay", symbol="BTC/USDT", timeframe="4h", bars=bars)
    )


def test_missing_4h_candle_is_detected() -> None:
    bars = (_bar(_utc(0)), _bar(_utc(8), close="65410.00"))
    report = inspect_ohlcv(bars, "4h")
    assert report.has_issues is True
    assert report.is_contiguous is False
    assert report.missing_open_times == (_utc(4),)
    assert report.missing_count == 1
    assert report.unexpected_open_times == ()


def test_multiple_missing_candles_are_counted() -> None:
    bars = (_bar(_utc(0)), _bar(_utc(12), close="65350.25"))
    report = inspect_ohlcv(bars, "4h")
    assert report.missing_open_times == (_utc(4), _utc(8))
    assert report.missing_count == 2


def test_off_grid_open_time_is_unexpected() -> None:
    bars = (_bar(_utc(0)), _bar(_utc(4), close="65020.00"), _bar(_utc(9), close="65410.00"))
    report = inspect_ohlcv(bars, "4h")
    assert report.has_issues is True
    assert report.missing_open_times == (_utc(8),)
    assert report.unexpected_open_times == (_utc(9),)
    assert _utc(9) in report.epoch_misaligned_open_times


def test_epoch_misaligned_first_bar_is_detected() -> None:
    bars = (_bar(_utc(1)),)
    report = inspect_ohlcv(bars, "4h")
    assert report.is_contiguous is True
    assert report.is_epoch_aligned is False
    assert report.has_issues is True
    assert report.epoch_misaligned_open_times == (_utc(1),)


def test_raw_out_of_order_input_is_detected_but_not_an_integrity_failure() -> None:
    first = _bar(_utc(0))
    second = _bar(_utc(4), close="65020.00")
    report = inspect_ohlcv((second, first), "4h")
    assert report.input_was_unordered is True
    assert report.has_issues is False
    assert (
        normalize_bars((second, first))[0].open_time < normalize_bars((second, first))[1].open_time
    )


def test_empty_and_single_bar_windows_are_contiguous() -> None:
    empty = inspect_ohlcv((), "4h")
    assert empty.bar_count == 0
    assert empty.has_issues is False
    single = inspect_ohlcv((_bar(_utc(0)),), "4h")
    assert single.bar_count == 1
    assert single.has_issues is False


def test_reported_missing_times_can_be_truncated() -> None:
    bars = (_bar(_utc(0)), _bar(_utc(16), close="64990.00"))
    report = inspect_ohlcv(bars, "4h", max_reported=2)
    assert report.missing_count == 3
    assert report.missing_open_times == (_utc(4), _utc(8))
    assert report.truncated is True


def test_require_contiguous_raises_with_report() -> None:
    series = OhlcvSeries.from_bars(
        provider="replay",
        symbol="BTC/USDT",
        timeframe="4h",
        bars=(_bar(_utc(0)), _bar(_utc(8), close="65410.00")),
    )
    with pytest.raises(IncompleteOhlcvHistory, match="missing=1") as exc_info:
        require_contiguous_ohlcv(series)
    assert exc_info.value.report.missing_open_times == (_utc(4),)


def test_weekly_series_uses_seven_day_steps_not_epoch_weekday() -> None:
    monday = datetime(2026, 8, 3, tzinfo=UTC)
    next_monday = monday + timedelta(days=7)
    bars = (_bar(monday), _bar(next_monday, close="65020.00"))
    report = inspect_ohlcv(bars, "1w")
    assert report.has_issues is False
    assert report.epoch_misaligned_open_times == ()


def test_daily_utc_midnight_is_epoch_aligned() -> None:
    first = datetime(2026, 8, 1, tzinfo=UTC)
    second = datetime(2026, 8, 2, tzinfo=UTC)
    report = inspect_ohlcv((_bar(first), _bar(second, close="65020.00")), "1d")
    assert report.has_issues is False
    skewed = inspect_ohlcv((_bar(datetime(2026, 8, 1, 12, tzinfo=UTC)),), "1d")
    assert skewed.has_issues is True
    assert skewed.is_epoch_aligned is False


def test_replay_fixture_is_contiguous_4h() -> None:
    provider = ReplayMarketDataProvider.from_json_path(FIXTURE_PATH)
    series = asyncio.run(provider.fetch_ohlcv("BTC/USDT", "4h", start=_utc(0), end=_utc(20)))
    report = inspect_series(series)
    assert report.has_issues is False
    assert report.bar_count == 6
    assert report.input_was_unordered is False
    require_contiguous_ohlcv(series)


def test_inspect_series_does_not_see_pre_normalize_order() -> None:
    series = OhlcvSeries.from_bars(
        provider="replay",
        symbol="BTC/USDT",
        timeframe="4h",
        bars=(_bar(_utc(4), close="65020.00"), _bar(_utc(0))),
    )
    report = inspect_series(series)
    assert report.input_was_unordered is False
    assert [bar.open_time for bar in series.bars] == [_utc(0), _utc(4)]


def test_log_integrity_issues_warns_on_gaps() -> None:
    series = OhlcvSeries.from_bars(
        provider="replay",
        symbol="BTC/USDT",
        timeframe="4h",
        bars=(_bar(_utc(0)), _bar(_utc(8), close="65410.00")),
    )
    with patch("app.market_data.integrity.logger.warning") as warning:
        report = log_integrity_issues(series)
    assert report.missing_count == 1
    warning.assert_called_once()
    message = warning.call_args.args[0] % warning.call_args.args[1:]
    assert "ohlcv integrity issues" in message
    assert "missing=1" in message
