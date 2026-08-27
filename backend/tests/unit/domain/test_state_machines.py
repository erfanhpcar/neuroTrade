from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.errors import InvalidStateTransition
from app.domain.order import (
    ORDER_TRANSITIONS,
    TERMINAL_ORDER_STATUSES,
    Order,
    OrderStatus,
    PositionSide,
)
from app.domain.position import POSITION_TRANSITIONS, Position, PositionStatus


def _utc() -> datetime:
    return datetime(2026, 8, 27, 12, 0, tzinfo=UTC)


def _order(status: OrderStatus, filled: str = "0") -> Order:
    quantity = Decimal("1")
    filled_qty = Decimal(filled)
    return Order(
        order_id=uuid4(),
        client_order_id="nt-order-1",
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        quantity=quantity,
        filled_quantity=filled_qty,
        status=status,
        created_at=_utc(),
    )


def test_happy_path_order_lifecycle() -> None:
    order = _order(OrderStatus.CREATED)
    order = order.transition(OrderStatus.RISK_APPROVED)
    order = order.transition(OrderStatus.SUBMITTING)
    order = order.transition(OrderStatus.SUBMITTED, exchange_order_id="ex-1")
    order = order.transition(OrderStatus.PARTIALLY_FILLED, filled_quantity=Decimal("0.4"))
    order = order.transition(OrderStatus.FILLED, filled_quantity=Decimal("1"))
    assert order.status is OrderStatus.FILLED
    assert order.exchange_order_id == "ex-1"


def test_created_may_be_rejected_by_risk() -> None:
    order = _order(OrderStatus.CREATED).transition(OrderStatus.REJECTED)
    assert order.status is OrderStatus.REJECTED


def test_risk_approved_may_cancel_before_submit() -> None:
    order = _order(OrderStatus.CREATED).transition(OrderStatus.RISK_APPROVED)
    canceled = order.transition(OrderStatus.CANCELED)
    assert canceled.status is OrderStatus.CANCELED


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (OrderStatus.CREATED, OrderStatus.SUBMITTED),
        (OrderStatus.CREATED, OrderStatus.FILLED),
        (OrderStatus.RISK_APPROVED, OrderStatus.SUBMITTED),
        (OrderStatus.SUBMITTING, OrderStatus.FILLED),
        (OrderStatus.SUBMITTED, OrderStatus.RISK_APPROVED),
        (OrderStatus.FILLED, OrderStatus.CANCELED),
        (OrderStatus.REJECTED, OrderStatus.CREATED),
        (OrderStatus.FAILED, OrderStatus.SUBMITTED),
        (OrderStatus.CANCELED, OrderStatus.SUBMITTED),
        (OrderStatus.CREATED, OrderStatus.CANCELED),
        (OrderStatus.PARTIALLY_FILLED, OrderStatus.SUBMITTED),
    ],
)
def test_invalid_order_transitions_are_rejected(current: OrderStatus, target: OrderStatus) -> None:
    filled = "0"
    if current is OrderStatus.PARTIALLY_FILLED:
        filled = "0.5"
    elif current is OrderStatus.FILLED:
        filled = "1"
    order = _order(current, filled=filled)
    with pytest.raises(InvalidStateTransition) as exc_info:
        order.transition(target)
    assert exc_info.value.entity == "order"
    assert exc_info.value.current == current.value
    assert exc_info.value.target == target.value


def test_terminal_order_statuses_have_no_exits() -> None:
    for status in TERMINAL_ORDER_STATUSES:
        assert ORDER_TRANSITIONS[status] == frozenset()


def test_filled_quantity_must_match_partial_status() -> None:
    with pytest.raises(ValueError, match="PARTIALLY_FILLED"):
        _order(OrderStatus.PARTIALLY_FILLED, filled="0")
    with pytest.raises(ValueError, match="FILLED"):
        _order(OrderStatus.FILLED, filled="0.5")
    with pytest.raises(ValueError, match="cannot exceed"):
        _order(OrderStatus.SUBMITTED, filled="2")


def test_cannot_skip_position_opening() -> None:
    position = Position(
        position_id=uuid4(),
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        status=PositionStatus.OPENING,
        quantity=Decimal("1"),
        avg_entry_price=Decimal("100"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("0"),
        opened_at=_utc(),
    )
    with pytest.raises(InvalidStateTransition):
        position.transition(PositionStatus.CLOSING)
    with pytest.raises(InvalidStateTransition):
        position.transition(PositionStatus.CLOSED)
    opened = position.transition(PositionStatus.OPEN)
    with pytest.raises(InvalidStateTransition):
        opened.transition(PositionStatus.CLOSED)
    closing = opened.transition(PositionStatus.CLOSING)
    closed = closing.transition(PositionStatus.CLOSED, quantity=Decimal("0"))
    assert closed.status is PositionStatus.CLOSED
    assert closed.quantity == 0


def test_closed_position_cannot_reopen() -> None:
    closed = Position(
        position_id=uuid4(),
        symbol="BTC/USDT",
        side=PositionSide.SHORT,
        status=PositionStatus.CLOSED,
        quantity=Decimal("0"),
        avg_entry_price=Decimal("100"),
        realized_pnl=Decimal("-1.5"),
        unrealized_pnl=Decimal("0"),
        opened_at=_utc(),
    )
    with pytest.raises(InvalidStateTransition):
        closed.transition(PositionStatus.OPEN)
    assert POSITION_TRANSITIONS[PositionStatus.CLOSED] == frozenset()
