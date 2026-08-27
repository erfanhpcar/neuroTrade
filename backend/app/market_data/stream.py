"""Exchange-agnostic live market-data stream types.

Live ticker/candle updates are a delivery mechanism, not the source of truth.
Historical bars remain REST + Parquet. This module is free of HTTP, WebSocket
clients, CCXT, FastAPI, and execution/strategy imports.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from app.domain.fields import require_symbol, require_text, require_timeframe
from app.domain.market import OhlcvBar
from app.domain.money import require_positive_decimal
from app.domain.timestamps import require_utc


@dataclass(frozen=True)
class LiveTicker:
    """Last traded price from a public ticker stream."""

    provider: str
    symbol: str
    timestamp: datetime
    last_price: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", require_text(self.provider, field="provider"))
        object.__setattr__(self, "symbol", require_symbol(self.symbol))
        object.__setattr__(self, "timestamp", require_utc(self.timestamp, field="timestamp"))
        object.__setattr__(
            self, "last_price", require_positive_decimal(self.last_price, field="last_price")
        )


@dataclass(frozen=True)
class LiveCandleUpdate:
    """One kline push. ``confirm=True`` means the candle is closed.

    Unconfirmed updates carry the venue's in-progress OHLC (close is last
    traded price). They must not be treated as closed bars for Strategy or
    Backtest. See ISSUE-0014.
    """

    provider: str
    symbol: str
    timeframe: str
    bar: OhlcvBar
    confirm: bool
    event_time: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", require_text(self.provider, field="provider"))
        object.__setattr__(self, "symbol", require_symbol(self.symbol))
        object.__setattr__(self, "timeframe", require_timeframe(self.timeframe))
        object.__setattr__(self, "event_time", require_utc(self.event_time, field="event_time"))
        if not isinstance(self.bar, OhlcvBar):
            raise TypeError("bar must be OhlcvBar")
        if not isinstance(self.confirm, bool):
            raise TypeError("confirm must be bool")


LiveMarketEvent = LiveTicker | LiveCandleUpdate


def closed_bar(update: LiveCandleUpdate) -> OhlcvBar | None:
    """Return the bar only when the venue marked the candle closed."""

    if not update.confirm:
        return None
    return update.bar


@runtime_checkable
class LiveMarketDataStream(Protocol):
    """Public live ticker/candle stream. Implementations must not require API keys.

    ``subscribe`` yields until the caller stops iterating or the adapter is
    closed. Unconfirmed candles have ``confirm=False``.
    """

    @property
    def name(self) -> str:
        """Adapter identity such as ``bybit``."""

    def subscribe(
        self,
        symbol: str,
        timeframe: str,
    ) -> AsyncIterator[LiveMarketEvent]:
        """Yield live ticker and candle updates for one symbol/timeframe."""
