"""Portfolio state visible to Strategy and Risk. This is not a live exchange snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.errors import DomainError
from app.domain.money import decimal_to_text, parse_decimal, require_non_negative_decimal
from app.domain.timestamps import require_utc


@dataclass(frozen=True)
class PortfolioState:
    """Account-level view injected into Strategy.generate_signal() and Risk."""

    as_of: datetime
    equity: Decimal
    cash_balance: Decimal
    open_position_count: int
    open_risk_pct: Decimal
    daily_realized_pnl: Decimal
    daily_unrealized_pnl: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "as_of", require_utc(self.as_of, field="as_of"))
        object.__setattr__(self, "equity", parse_decimal(self.equity, field="equity"))
        object.__setattr__(
            self, "cash_balance", parse_decimal(self.cash_balance, field="cash_balance")
        )
        if not isinstance(self.open_position_count, int) or isinstance(
            self.open_position_count, bool
        ):
            raise DomainError("open_position_count must be int")
        if self.open_position_count < 0:
            raise DomainError("open_position_count must be >= 0")
        object.__setattr__(
            self,
            "open_risk_pct",
            require_non_negative_decimal(self.open_risk_pct, field="open_risk_pct"),
        )
        object.__setattr__(
            self,
            "daily_realized_pnl",
            parse_decimal(self.daily_realized_pnl, field="daily_realized_pnl"),
        )
        object.__setattr__(
            self,
            "daily_unrealized_pnl",
            parse_decimal(self.daily_unrealized_pnl, field="daily_unrealized_pnl"),
        )

    def to_wire(self) -> dict[str, str | int]:
        return {
            "as_of": self.as_of.isoformat(),
            "equity": decimal_to_text(self.equity),
            "cash_balance": decimal_to_text(self.cash_balance),
            "open_position_count": self.open_position_count,
            "open_risk_pct": decimal_to_text(self.open_risk_pct),
            "daily_realized_pnl": decimal_to_text(self.daily_realized_pnl),
            "daily_unrealized_pnl": decimal_to_text(self.daily_unrealized_pnl),
        }
