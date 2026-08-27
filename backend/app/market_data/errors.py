"""Market-data boundary errors. These are not HTTP or persistence errors."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.market_data.integrity import OhlcvIntegrityReport


class MarketDataError(ValueError):
    """Invalid market-data input, payload, or provider lookup."""


class InvalidMarketDataRange(MarketDataError):
    """``start`` is after ``end`` for an OHLCV query."""


class UnknownMarketSeries(MarketDataError):
    """The provider has no series for the requested symbol/timeframe."""


class InsufficientMarketHistory(MarketDataError):
    """No closed bar exists at or before the requested snapshot timestamp."""


class ConflictingDuplicateBars(MarketDataError):
    """Two bars share ``open_time`` but disagree on OHLCV values."""


class IncompleteOhlcvHistory(MarketDataError):
    """OHLCV bars are gapped, off the timeframe grid, or epoch-misaligned.

    The detector report is attached as ``report`` so callers can log missing
    open times without parsing the message.
    """

    def __init__(self, message: str, *, report: OhlcvIntegrityReport) -> None:
        super().__init__(message)
        self.report = report


class UnsupportedTimeframe(MarketDataError):
    """The venue adapter has no mapping for the requested timeframe."""


class UnsupportedMarketCategory(MarketDataError):
    """The venue adapter does not accept the requested product category."""


class MarketDataHttpError(MarketDataError):
    """Public REST call failed after retries or returned a non-success body."""


class MarketDataRateLimited(MarketDataHttpError):
    """The venue rejected the request for exceeding its documented rate limit."""
