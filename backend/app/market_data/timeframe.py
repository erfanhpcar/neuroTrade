"""Fixed durations for OHLCV gap detection.

Timeframe strings stay opaque in domain models. This module is the market-data
boundary that knows how long a candle is. Calendar months (``1M``) are not a
fixed ``timedelta`` and are rejected here rather than guessed.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from app.domain.fields import require_timeframe
from app.market_data.errors import UnsupportedTimeframe

# Matches the Bybit public kline set except calendar ``1M``.
TIMEFRAME_DURATION: Final[dict[str, timedelta]] = {
    "1m": timedelta(minutes=1),
    "3m": timedelta(minutes=3),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "2h": timedelta(hours=2),
    "4h": timedelta(hours=4),
    "6h": timedelta(hours=6),
    "12h": timedelta(hours=12),
    "1d": timedelta(days=1),
    "1w": timedelta(days=7),
}

# Sub-week candles are Unix-epoch aligned on crypto venues (UTC). Weekly bars
# are a 7-day step from the first bar; weekday of week-start is venue-specific.
EPOCH_ALIGNED_TIMEFRAMES: Final[frozenset[str]] = frozenset(
    key for key in TIMEFRAME_DURATION if key != "1w"
)


def timeframe_duration(timeframe: str) -> timedelta:
    """Return the fixed bar length. Raises if the timeframe is not a fixed duration."""

    key = require_timeframe(timeframe)
    try:
        return TIMEFRAME_DURATION[key]
    except KeyError as exc:
        raise UnsupportedTimeframe(
            f"timeframe {key!r} has no fixed duration for gap detection"
        ) from exc


def timeframe_duration_seconds(timeframe: str) -> int:
    """Return bar length in whole seconds."""

    duration = timeframe_duration(timeframe)
    seconds = int(duration.total_seconds())
    if timedelta(seconds=seconds) != duration:
        raise UnsupportedTimeframe(f"timeframe {timeframe!r} is not a whole-second duration")
    return seconds


def uses_epoch_alignment(timeframe: str) -> bool:
    key = require_timeframe(timeframe)
    if key not in TIMEFRAME_DURATION:
        raise UnsupportedTimeframe(f"timeframe {key!r} has no fixed duration for gap detection")
    return key in EPOCH_ALIGNED_TIMEFRAMES
