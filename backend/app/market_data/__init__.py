"""Public market-data adapter contract.

Domain types stay in ``app.domain``. Contract modules in this package must not
import FastAPI, SQLAlchemy, CCXT, HTTP clients, or ``app.execution``.
Venue adapters such as ``bybit.py`` may use ``httpx`` at the network boundary.
Import adapters directly (``app.market_data.bybit``) so this package import
stays HTTP-free for replay/unit tests.
"""

from app.market_data.base import (
    OHLCV_SCHEMA_VERSION,
    MarketDataProvider,
    OhlcvSeries,
    hash_ohlcv_bars,
    normalize_bars,
)
from app.market_data.errors import (
    ConflictingDuplicateBars,
    IncompleteOhlcvHistory,
    InsufficientMarketHistory,
    InvalidMarketDataRange,
    MarketDataError,
    MarketDataHttpError,
    MarketDataRateLimited,
    UnknownMarketSeries,
    UnsupportedMarketCategory,
    UnsupportedTimeframe,
)
from app.market_data.integrity import (
    OhlcvIntegrityReport,
    inspect_ohlcv,
    inspect_series,
    require_contiguous_ohlcv,
)
from app.market_data.replay import ReplayMarketDataProvider
from app.market_data.timeframe import timeframe_duration, timeframe_duration_seconds

__all__ = [
    "OHLCV_SCHEMA_VERSION",
    "ConflictingDuplicateBars",
    "IncompleteOhlcvHistory",
    "InsufficientMarketHistory",
    "InvalidMarketDataRange",
    "MarketDataError",
    "MarketDataHttpError",
    "MarketDataProvider",
    "MarketDataRateLimited",
    "OhlcvIntegrityReport",
    "OhlcvSeries",
    "ReplayMarketDataProvider",
    "UnknownMarketSeries",
    "UnsupportedMarketCategory",
    "UnsupportedTimeframe",
    "hash_ohlcv_bars",
    "inspect_ohlcv",
    "inspect_series",
    "normalize_bars",
    "require_contiguous_ohlcv",
    "timeframe_duration",
    "timeframe_duration_seconds",
]
