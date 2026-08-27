"""Market snapshot available at a strategy decision timestamp.

A snapshot may only include information that existed at ``timestamp``.
The last closed bar's open time must not be after that timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.fields import require_symbol, require_text, require_timeframe
from app.domain.money import decimal_to_text, require_non_negative_decimal, require_positive_decimal
from app.domain.timestamps import require_utc


@dataclass(frozen=True)
class OhlcvBar:
    """One OHLCV candle. Prices and volume are Decimal."""

    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "open_time", require_utc(self.open_time, field="open_time"))
        object.__setattr__(self, "open", require_positive_decimal(self.open, field="open"))
        object.__setattr__(self, "high", require_positive_decimal(self.high, field="high"))
        object.__setattr__(self, "low", require_positive_decimal(self.low, field="low"))
        object.__setattr__(self, "close", require_positive_decimal(self.close, field="close"))
        object.__setattr__(
            self, "volume", require_non_negative_decimal(self.volume, field="volume")
        )
        if self.high < self.low:
            raise ValueError(f"high {self.high} is below low {self.low}")
        if self.high < self.open or self.high < self.close:
            raise ValueError("high must be >= open and close")
        if self.low > self.open or self.low > self.close:
            raise ValueError("low must be <= open and close")

    def to_wire(self) -> dict[str, str]:
        return {
            "open_time": self.open_time.isoformat(),
            "open": decimal_to_text(self.open),
            "high": decimal_to_text(self.high),
            "low": decimal_to_text(self.low),
            "close": decimal_to_text(self.close),
            "volume": decimal_to_text(self.volume),
        }


@dataclass(frozen=True)
class MarketSnapshot:
    """Point-in-time market view injected into Strategy.generate_signal()."""

    symbol: str
    timeframe: str
    timestamp: datetime
    bar: OhlcvBar
    provider: str
    dataset_hash: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", require_symbol(self.symbol))
        object.__setattr__(self, "timeframe", require_timeframe(self.timeframe))
        object.__setattr__(self, "timestamp", require_utc(self.timestamp, field="timestamp"))
        object.__setattr__(self, "provider", require_text(self.provider, field="provider"))
        if self.dataset_hash is not None:
            object.__setattr__(
                self, "dataset_hash", require_text(self.dataset_hash, field="dataset_hash")
            )
        if not isinstance(self.bar, OhlcvBar):
            raise TypeError("bar must be OhlcvBar")
        if self.bar.open_time > self.timestamp:
            raise ValueError("bar.open_time is after snapshot timestamp; that would be look-ahead")
