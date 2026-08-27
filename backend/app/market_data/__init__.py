"""Public market-data adapter contract.

Domain types stay in ``app.domain``. This package must not import FastAPI,
SQLAlchemy, CCXT, HTTP clients, or ``app.execution``.
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
    UnknownMarketSeries,
)
from app.market_data.replay import ReplayMarketDataProvider

__all__ = [
    "OHLCV_SCHEMA_VERSION",
    "ConflictingDuplicateBars",
    "InsufficientMarketHistory",
    "InvalidMarketDataRange",
    "MarketDataError",
    "MarketDataProvider",
    "OhlcvSeries",
    "ReplayMarketDataProvider",
    "UnknownMarketSeries",
    "hash_ohlcv_bars",
    "normalize_bars",
]
