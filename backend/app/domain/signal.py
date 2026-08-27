"""Strategy signal contract. Strategy emits Signal; it does not size or place orders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.domain.fields import require_symbol, require_text, require_timeframe, require_uuid
from app.domain.money import decimal_to_text, require_positive_decimal
from app.domain.timestamps import require_utc


class SignalSide(StrEnum):
    """Documented signal sides from docs/02_STRATEGY_ENGINE.md."""

    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


@dataclass(frozen=True)
class Signal:
    """Deterministic strategy output. ``position_size`` is intentionally absent."""

    signal_id: UUID
    strategy_name: str
    strategy_version: str
    symbol: str
    timeframe: str
    side: SignalSide
    trigger_price: Decimal
    stop_model: str
    exit_model: str
    created_at: datetime
    dataset_hash: str | None = None
    market_data_version: str | None = None
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "signal_id", require_uuid(self.signal_id, field="signal_id"))
        object.__setattr__(
            self, "strategy_name", require_text(self.strategy_name, field="strategy_name")
        )
        object.__setattr__(
            self, "strategy_version", require_text(self.strategy_version, field="strategy_version")
        )
        object.__setattr__(self, "symbol", require_symbol(self.symbol))
        object.__setattr__(self, "timeframe", require_timeframe(self.timeframe))
        if not isinstance(self.side, SignalSide):
            raise TypeError("side must be SignalSide")
        object.__setattr__(
            self,
            "trigger_price",
            require_positive_decimal(self.trigger_price, field="trigger_price"),
        )
        object.__setattr__(self, "stop_model", require_text(self.stop_model, field="stop_model"))
        object.__setattr__(self, "exit_model", require_text(self.exit_model, field="exit_model"))
        object.__setattr__(self, "created_at", require_utc(self.created_at, field="created_at"))
        if self.dataset_hash is not None:
            object.__setattr__(
                self, "dataset_hash", require_text(self.dataset_hash, field="dataset_hash")
            )
        if self.market_data_version is not None:
            object.__setattr__(
                self,
                "market_data_version",
                require_text(self.market_data_version, field="market_data_version"),
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    def to_wire(self) -> dict[str, object]:
        return {
            "signal_id": str(self.signal_id),
            "strategy_name": self.strategy_name,
            "strategy_version": self.strategy_version,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "side": self.side.value,
            "trigger_price": decimal_to_text(self.trigger_price),
            "stop_model": self.stop_model,
            "exit_model": self.exit_model,
            "created_at": self.created_at.isoformat(),
            "dataset_hash": self.dataset_hash,
            "market_data_version": self.market_data_version,
            "metadata": [list(pair) for pair in self.metadata],
        }


def _freeze_metadata(value: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, tuple):
        raise TypeError("metadata must be a tuple of (key, value) string pairs")
    frozen: list[tuple[str, str]] = []
    for item in value:
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError("metadata entries must be (str, str) pairs")
        key, raw = item
        frozen.append(
            (require_text(key, field="metadata.key"), require_text(raw, field="metadata.value"))
        )
    return tuple(frozen)
