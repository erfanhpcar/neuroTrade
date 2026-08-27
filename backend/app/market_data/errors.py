"""Market-data boundary errors. These are not HTTP or persistence errors."""


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
