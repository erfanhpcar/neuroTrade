"""Exchange-agnostic market-data contract.

Adapters may talk to a public REST/WebSocket API later. This module stays free of
HTTP clients, CCXT, FastAPI, SQLAlchemy, and execution/strategy imports.
OHLCV prices remain ``Decimal``. Timestamps remain timezone-aware UTC.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from app.domain.fields import require_symbol, require_text, require_timeframe
from app.domain.market import MarketSnapshot, OhlcvBar
from app.domain.money import decimal_to_text
from app.market_data.errors import ConflictingDuplicateBars

OHLCV_SCHEMA_VERSION = "ohlcv-v1"


def hash_ohlcv_bars(
    *,
    provider: str,
    symbol: str,
    timeframe: str,
    bars: Sequence[OhlcvBar],
    schema_version: str = OHLCV_SCHEMA_VERSION,
) -> str:
    """Return a stable SHA-256 hex digest of a canonical OHLCV series.

    The hash covers provider identity and bar contents, not download timestamps.
    """

    hasher = hashlib.sha256()
    hasher.update(f"{schema_version}\n{provider}\n{symbol}\n{timeframe}\n".encode())
    for bar in bars:
        hasher.update(
            (
                f"{bar.open_time.isoformat()}|"
                f"{decimal_to_text(bar.open)}|{decimal_to_text(bar.high)}|"
                f"{decimal_to_text(bar.low)}|{decimal_to_text(bar.close)}|"
                f"{decimal_to_text(bar.volume)}\n"
            ).encode()
        )
    return hasher.hexdigest()


def normalize_bars(bars: Sequence[OhlcvBar]) -> tuple[OhlcvBar, ...]:
    """Return UTC bars sorted by ``open_time``.

    Identical duplicates (same ``open_time`` and OHLCV) collapse to one bar.
    Conflicting duplicates raise ``ConflictingDuplicateBars`` instead of picking
    a winner. ``OhlcvBar`` already rejects naive / non-UTC timestamps.

    Sorting does not detect missing candles. Use ``inspect_ohlcv`` /
    ``inspect_series`` so gaps and off-grid timestamps are not ignored.
    """

    if not bars:
        return ()
    for bar in bars:
        if not isinstance(bar, OhlcvBar):
            raise TypeError(f"bars must be OhlcvBar, got {type(bar).__name__}")

    ordered = sorted(bars, key=lambda bar: bar.open_time)
    unique: list[OhlcvBar] = []
    for bar in ordered:
        if not unique:
            unique.append(bar)
            continue
        previous = unique[-1]
        if bar.open_time != previous.open_time:
            unique.append(bar)
            continue
        if bar != previous:
            raise ConflictingDuplicateBars(
                f"conflicting OHLCV bars at open_time {bar.open_time.isoformat()}"
            )
    return tuple(unique)


@dataclass(frozen=True)
class OhlcvSeries:
    """Normalized OHLCV window for one symbol/timeframe from one provider."""

    provider: str
    symbol: str
    timeframe: str
    bars: tuple[OhlcvBar, ...]
    dataset_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", require_text(self.provider, field="provider"))
        object.__setattr__(self, "symbol", require_symbol(self.symbol))
        object.__setattr__(self, "timeframe", require_timeframe(self.timeframe))
        object.__setattr__(
            self, "dataset_hash", require_text(self.dataset_hash, field="dataset_hash")
        )
        object.__setattr__(self, "bars", normalize_bars(self.bars))

    @classmethod
    def from_bars(
        cls,
        *,
        provider: str,
        symbol: str,
        timeframe: str,
        bars: Sequence[OhlcvBar],
        dataset_hash: str | None = None,
    ) -> OhlcvSeries:
        """Build a series, hashing contents when ``dataset_hash`` is omitted."""

        normalized = normalize_bars(bars)
        digest = dataset_hash or hash_ohlcv_bars(
            provider=provider,
            symbol=symbol,
            timeframe=timeframe,
            bars=normalized,
        )
        return cls(
            provider=provider,
            symbol=symbol,
            timeframe=timeframe,
            bars=normalized,
            dataset_hash=digest,
        )


@runtime_checkable
class MarketDataProvider(Protocol):
    """Public market-data contract. Implementations must not require API keys.

    ``fetch_ohlcv`` returns closed bars whose ``open_time`` is in the inclusive
    UTC range ``[start, end]``, already sorted and de-duplicated.

    ``latest_snapshot`` returns the last bar with ``open_time <= timestamp``.
    That matches the current ``MarketSnapshot`` look-ahead guard. Whether a bar
    should instead be withheld until it closes is ISSUE-0014.

    Returned series are sorted and de-duplicated. Callers must run
    ``inspect_series`` (or ``require_contiguous_ohlcv``) before treating the
    window as a complete grid. Providers log integrity issues; they do not
    raise on gaps. Live ticker/candle streaming is not part of this increment.
    """

    @property
    def name(self) -> str:
        """Adapter identity such as ``replay`` or a later public venue name."""

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        *,
        start: datetime,
        end: datetime,
    ) -> OhlcvSeries:
        """Return historical closed bars. Empty range is an empty series, not an error."""

    async def latest_snapshot(
        self,
        symbol: str,
        timeframe: str,
        *,
        timestamp: datetime,
    ) -> MarketSnapshot:
        """Point-in-time snapshot for Strategy. Must not use a bar after ``timestamp``."""
