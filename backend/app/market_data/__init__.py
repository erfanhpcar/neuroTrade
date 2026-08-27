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
    InsufficientMarketHistory,
    InvalidMarketDataRange,
    MarketDataError,
    MarketDataHttpError,
    MarketDataRateLimited,
    UnknownMarketSeries,
    UnsupportedMarketCategory,
    UnsupportedTimeframe,
)
from app.market_data.replay import ReplayMarketDataProvider

__all__ = [
    "OHLCV_SCHEMA_VERSION",
    "ConflictingDuplicateBars",
    "InsufficientMarketHistory",
    "InvalidMarketDataRange",
    "MarketDataError",
    "MarketDataHttpError",
    "MarketDataProvider",
    "MarketDataRateLimited",
    "OhlcvSeries",
    "ReplayMarketDataProvider",
    "UnknownMarketSeries",
    "UnsupportedMarketCategory",
    "UnsupportedTimeframe",
    "hash_ohlcv_bars",
    "normalize_bars",
]
