"""Order intent, order, fill, and the documented order state machine."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.domain.fields import require_client_order_id, require_symbol, require_text, require_uuid
from app.domain.money import (
    decimal_to_text,
    require_non_negative_decimal,
    require_positive_decimal,
)
from app.domain.state import assert_allowed_transition
from app.domain.timestamps import require_utc


class PositionSide(StrEnum):
    """Intended position direction. Exchange BUY/SELL mapping is an execution concern."""

    LONG = "LONG"
    SHORT = "SHORT"


class OrderStatus(StrEnum):
    """Order states from docs/04_DATA_SCHEMAS.md."""

    CREATED = "CREATED"
    RISK_APPROVED = "RISK_APPROVED"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


ORDER_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.CREATED: frozenset({OrderStatus.RISK_APPROVED, OrderStatus.REJECTED}),
    OrderStatus.RISK_APPROVED: frozenset({OrderStatus.SUBMITTING, OrderStatus.CANCELED}),
    OrderStatus.SUBMITTING: frozenset(
        {OrderStatus.SUBMITTED, OrderStatus.REJECTED, OrderStatus.FAILED}
    ),
    OrderStatus.SUBMITTED: frozenset(
        {
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
            OrderStatus.FAILED,
        }
    ),
    OrderStatus.PARTIALLY_FILLED: frozenset(
        {OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.FAILED}
    ),
    OrderStatus.FILLED: frozenset(),
    OrderStatus.CANCELED: frozenset(),
    OrderStatus.REJECTED: frozenset(),
    OrderStatus.FAILED: frozenset(),
}

TERMINAL_ORDER_STATUSES = frozenset(
    {OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REJECTED, OrderStatus.FAILED}
)


@dataclass(frozen=True)
class OrderIntent:
    """Risk-approved intent handed to Execution. Strategy never constructs this."""

    intent_id: UUID
    signal_id: UUID
    risk_decision_id: UUID
    client_order_id: str
    symbol: str
    side: PositionSide
    quantity: Decimal
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "intent_id", require_uuid(self.intent_id, field="intent_id"))
        object.__setattr__(self, "signal_id", require_uuid(self.signal_id, field="signal_id"))
        object.__setattr__(
            self, "risk_decision_id", require_uuid(self.risk_decision_id, field="risk_decision_id")
        )
        object.__setattr__(self, "client_order_id", require_client_order_id(self.client_order_id))
        object.__setattr__(self, "symbol", require_symbol(self.symbol))
        if not isinstance(self.side, PositionSide):
            raise TypeError("side must be PositionSide")
        object.__setattr__(
            self, "quantity", require_positive_decimal(self.quantity, field="quantity")
        )
        object.__setattr__(self, "created_at", require_utc(self.created_at, field="created_at"))

    def to_wire(self) -> dict[str, str]:
        return {
            "intent_id": str(self.intent_id),
            "signal_id": str(self.signal_id),
            "risk_decision_id": str(self.risk_decision_id),
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": decimal_to_text(self.quantity),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class Order:
    """Internal order aggregate. ``exchange_order_id`` is distinct from ``order_id``."""

    order_id: UUID
    client_order_id: str
    symbol: str
    side: PositionSide
    quantity: Decimal
    filled_quantity: Decimal
    status: OrderStatus
    created_at: datetime
    signal_id: UUID | None = None
    risk_decision_id: UUID | None = None
    exchange_order_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "order_id", require_uuid(self.order_id, field="order_id"))
        object.__setattr__(self, "client_order_id", require_client_order_id(self.client_order_id))
        object.__setattr__(self, "symbol", require_symbol(self.symbol))
        if not isinstance(self.side, PositionSide):
            raise TypeError("side must be PositionSide")
        object.__setattr__(
            self, "quantity", require_positive_decimal(self.quantity, field="quantity")
        )
        object.__setattr__(
            self,
            "filled_quantity",
            require_non_negative_decimal(self.filled_quantity, field="filled_quantity"),
        )
        if not isinstance(self.status, OrderStatus):
            raise TypeError("status must be OrderStatus")
        object.__setattr__(self, "created_at", require_utc(self.created_at, field="created_at"))
        if self.signal_id is not None:
            object.__setattr__(self, "signal_id", require_uuid(self.signal_id, field="signal_id"))
        if self.risk_decision_id is not None:
            object.__setattr__(
                self,
                "risk_decision_id",
                require_uuid(self.risk_decision_id, field="risk_decision_id"),
            )
        if self.exchange_order_id is not None:
            object.__setattr__(
                self,
                "exchange_order_id",
                require_text(self.exchange_order_id, field="exchange_order_id"),
            )
        _assert_fill_matches_status(self.status, self.quantity, self.filled_quantity)

    def transition(
        self,
        new_status: OrderStatus,
        *,
        filled_quantity: Decimal | None = None,
        exchange_order_id: str | None = None,
    ) -> Order:
        """Return a new Order in ``new_status``. Does not call the clock."""

        assert_allowed_transition("order", self.status, new_status, ORDER_TRANSITIONS)
        next_filled = self.filled_quantity if filled_quantity is None else filled_quantity
        next_exchange_id = (
            self.exchange_order_id if exchange_order_id is None else exchange_order_id
        )
        return replace(
            self, status=new_status, filled_quantity=next_filled, exchange_order_id=next_exchange_id
        )

    def to_wire(self) -> dict[str, str | None]:
        return {
            "order_id": str(self.order_id),
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": decimal_to_text(self.quantity),
            "filled_quantity": decimal_to_text(self.filled_quantity),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "signal_id": None if self.signal_id is None else str(self.signal_id),
            "risk_decision_id": None
            if self.risk_decision_id is None
            else str(self.risk_decision_id),
            "exchange_order_id": self.exchange_order_id,
        }


@dataclass(frozen=True)
class Fill:
    """A fill against an order. Fees are Decimal and non-negative."""

    fill_id: UUID
    order_id: UUID
    client_order_id: str
    quantity: Decimal
    price: Decimal
    fee: Decimal
    filled_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "fill_id", require_uuid(self.fill_id, field="fill_id"))
        object.__setattr__(self, "order_id", require_uuid(self.order_id, field="order_id"))
        object.__setattr__(self, "client_order_id", require_client_order_id(self.client_order_id))
        object.__setattr__(
            self, "quantity", require_positive_decimal(self.quantity, field="quantity")
        )
        object.__setattr__(self, "price", require_positive_decimal(self.price, field="price"))
        object.__setattr__(self, "fee", require_non_negative_decimal(self.fee, field="fee"))
        object.__setattr__(self, "filled_at", require_utc(self.filled_at, field="filled_at"))

    def to_wire(self) -> dict[str, str]:
        return {
            "fill_id": str(self.fill_id),
            "order_id": str(self.order_id),
            "client_order_id": self.client_order_id,
            "quantity": decimal_to_text(self.quantity),
            "price": decimal_to_text(self.price),
            "fee": decimal_to_text(self.fee),
            "filled_at": self.filled_at.isoformat(),
        }


def _assert_fill_matches_status(
    status: OrderStatus, quantity: Decimal, filled_quantity: Decimal
) -> None:
    if filled_quantity > quantity:
        raise ValueError("filled_quantity cannot exceed quantity")
    if status in {OrderStatus.CREATED, OrderStatus.RISK_APPROVED, OrderStatus.SUBMITTING}:
        if filled_quantity != 0:
            raise ValueError(f"{status.value} orders must have filled_quantity 0")
    if status is OrderStatus.SUBMITTED and filled_quantity != 0:
        raise ValueError("SUBMITTED orders must have filled_quantity 0 until a fill arrives")
    if status is OrderStatus.PARTIALLY_FILLED and not (0 < filled_quantity < quantity):
        raise ValueError("PARTIALLY_FILLED orders must have 0 < filled_quantity < quantity")
    if status is OrderStatus.FILLED and filled_quantity != quantity:
        raise ValueError("FILLED orders must have filled_quantity == quantity")
