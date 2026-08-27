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


class UnsupportedTimeframe(MarketDataError):
    """The venue adapter has no mapping for the requested timeframe."""


class UnsupportedMarketCategory(MarketDataError):
    """The venue adapter does not accept the requested product category."""


class MarketDataHttpError(MarketDataError):
    """Public REST call failed after retries or returned a non-success body."""


class MarketDataRateLimited(MarketDataHttpError):
    """The venue rejected the request for exceeding its documented rate limit."""
