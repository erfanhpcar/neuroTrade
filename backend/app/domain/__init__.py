"""Framework-independent trading domain types.

This package must not import FastAPI, SQLAlchemy, CCXT, Redis, or HTTP clients.
"""

from app.domain.errors import (
    DomainError,
    InvalidFinancialValue,
    InvalidStateTransition,
    InvalidTimestamp,
)
from app.domain.market import MarketSnapshot, OhlcvBar
from app.domain.money import decimal_from_text, decimal_to_text, parse_decimal
from app.domain.order import (
    ORDER_TRANSITIONS,
    TERMINAL_ORDER_STATUSES,
    Fill,
    Order,
    OrderIntent,
    OrderStatus,
    PositionSide,
)
from app.domain.portfolio import PortfolioState
from app.domain.position import POSITION_TRANSITIONS, Position, PositionStatus
from app.domain.risk import RiskDecision, RiskVerdict
from app.domain.signal import Signal, SignalSide

__all__ = [
    "DomainError",
    "Fill",
    "InvalidFinancialValue",
    "InvalidStateTransition",
    "InvalidTimestamp",
    "MarketSnapshot",
    "OhlcvBar",
    "ORDER_TRANSITIONS",
    "Order",
    "OrderIntent",
    "OrderStatus",
    "POSITION_TRANSITIONS",
    "PortfolioState",
    "Position",
    "PositionSide",
    "PositionStatus",
    "RiskDecision",
    "RiskVerdict",
    "Signal",
    "SignalSide",
    "TERMINAL_ORDER_STATUSES",
    "decimal_from_text",
    "decimal_to_text",
    "parse_decimal",
]
