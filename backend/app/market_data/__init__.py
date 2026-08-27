"""Public market-data adapter contract.

Domain types stay in ``app.domain``. Contract modules in this package must not
import FastAPI, SQLAlchemy, CCXT, HTTP clients, WebSocket clients, or
``app.execution``. Venue adapters such as ``bybit.py`` may use ``httpx`` and
``bybit_ws.py`` may use ``websockets`` at the network boundary. Import adapters
directly so this package import stays HTTP/WS-free for replay/unit tests.
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
    CorruptOhlcvDataset,
    EmptyOhlcvDataset,
    ImmutableOhlcvDataset,
    IncompleteOhlcvHistory,
    InsufficientMarketHistory,
    InvalidMarketDataRange,
    MarketDataError,
    MarketDataHttpError,
    MarketDataRateLimited,
    MarketDataStreamDisconnected,
    MarketDataStreamError,
    UnknownMarketSeries,
    UnknownOhlcvDataset,
    UnsupportedMarketCategory,
    UnsupportedTimeframe,
)
from app.market_data.integrity import (
    OhlcvIntegrityReport,
    inspect_ohlcv,
    inspect_series,
    require_contiguous_ohlcv,
)
from app.market_data.parquet import (
    OhlcvDatasetManifest,
    OhlcvParquetFile,
    ParquetOhlcvStore,
    path_symbol,
)
from app.market_data.reconnect import (
    DEFAULT_WS_RECONNECT,
    ReconnectPolicy,
    reconnect_backoff_seconds,
)
from app.market_data.replay import ReplayMarketDataProvider
from app.market_data.stream import (
    LiveCandleUpdate,
    LiveMarketDataStream,
    LiveMarketEvent,
    LiveTicker,
    closed_bar,
)
from app.market_data.timeframe import timeframe_duration, timeframe_duration_seconds

__all__ = [
    "OHLCV_SCHEMA_VERSION",
    "ConflictingDuplicateBars",
    "CorruptOhlcvDataset",
    "EmptyOhlcvDataset",
    "ImmutableOhlcvDataset",
    "IncompleteOhlcvHistory",
    "DEFAULT_WS_RECONNECT",
    "InsufficientMarketHistory",
    "InvalidMarketDataRange",
    "LiveCandleUpdate",
    "LiveMarketDataStream",
    "LiveMarketEvent",
    "LiveTicker",
    "MarketDataError",
    "MarketDataHttpError",
    "MarketDataProvider",
    "MarketDataRateLimited",
    "MarketDataStreamDisconnected",
    "MarketDataStreamError",
    "OhlcvDatasetManifest",
    "OhlcvIntegrityReport",
    "OhlcvParquetFile",
    "OhlcvSeries",
    "ParquetOhlcvStore",
    "ReconnectPolicy",
    "ReplayMarketDataProvider",
    "UnknownMarketSeries",
    "UnknownOhlcvDataset",
    "UnsupportedMarketCategory",
    "UnsupportedTimeframe",
    "closed_bar",
    "hash_ohlcv_bars",
    "inspect_ohlcv",
    "inspect_series",
    "normalize_bars",
    "path_symbol",
    "reconnect_backoff_seconds",
    "require_contiguous_ohlcv",
    "timeframe_duration",
    "timeframe_duration_seconds",
]
