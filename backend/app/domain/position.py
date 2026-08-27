"""Position aggregate and the documented position state machine."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.domain.fields import require_symbol, require_uuid
from app.domain.money import (
    decimal_to_text,
    parse_decimal,
    require_non_negative_decimal,
    require_positive_decimal,
)
from app.domain.order import PositionSide
from app.domain.state import assert_allowed_transition
from app.domain.timestamps import require_utc


class PositionStatus(StrEnum):
    """Position states from docs/04_DATA_SCHEMAS.md."""

    OPENING = "OPENING"
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"


POSITION_TRANSITIONS: dict[PositionStatus, frozenset[PositionStatus]] = {
    PositionStatus.OPENING: frozenset({PositionStatus.OPEN}),
    PositionStatus.OPEN: frozenset({PositionStatus.CLOSING}),
    PositionStatus.CLOSING: frozenset({PositionStatus.CLOSED}),
    PositionStatus.CLOSED: frozenset(),
}


@dataclass(frozen=True)
class Position:
    """One symbol position. Quantity is zero only when CLOSED."""

    position_id: UUID
    symbol: str
    side: PositionSide
    status: PositionStatus
    quantity: Decimal
    avg_entry_price: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    opened_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "position_id", require_uuid(self.position_id, field="position_id"))
        object.__setattr__(self, "symbol", require_symbol(self.symbol))
        if not isinstance(self.side, PositionSide):
            raise TypeError("side must be PositionSide")
        if not isinstance(self.status, PositionStatus):
            raise TypeError("status must be PositionStatus")
        object.__setattr__(
            self,
            "avg_entry_price",
            require_positive_decimal(self.avg_entry_price, field="avg_entry_price"),
        )
        object.__setattr__(
            self, "realized_pnl", parse_decimal(self.realized_pnl, field="realized_pnl")
        )
        object.__setattr__(
            self, "unrealized_pnl", parse_decimal(self.unrealized_pnl, field="unrealized_pnl")
        )
        object.__setattr__(self, "opened_at", require_utc(self.opened_at, field="opened_at"))
        if self.status is PositionStatus.CLOSED:
            object.__setattr__(
                self, "quantity", require_non_negative_decimal(self.quantity, field="quantity")
            )
            if self.quantity != 0:
                raise ValueError("CLOSED positions must have quantity 0")
        else:
            object.__setattr__(
                self, "quantity", require_positive_decimal(self.quantity, field="quantity")
            )

    def transition(
        self, new_status: PositionStatus, *, quantity: Decimal | None = None
    ) -> Position:
        assert_allowed_transition("position", self.status, new_status, POSITION_TRANSITIONS)
        next_quantity = self.quantity if quantity is None else quantity
        return replace(self, status=new_status, quantity=next_quantity)

    def to_wire(self) -> dict[str, str]:
        return {
            "position_id": str(self.position_id),
            "symbol": self.symbol,
            "side": self.side.value,
            "status": self.status.value,
            "quantity": decimal_to_text(self.quantity),
            "avg_entry_price": decimal_to_text(self.avg_entry_price),
            "realized_pnl": decimal_to_text(self.realized_pnl),
            "unrealized_pnl": decimal_to_text(self.unrealized_pnl),
            "opened_at": self.opened_at.isoformat(),
        }
