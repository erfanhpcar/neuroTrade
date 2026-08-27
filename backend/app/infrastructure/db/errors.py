"""Persistence-boundary errors. Messages must not include secrets or DSNs."""

from __future__ import annotations

import re

from sqlalchemy.exc import IntegrityError

_KEY_ALREADY_EXISTS = re.compile(
    r"Key \((?P<column>[^)]+)\)=\((?P<value>[^)]*)\) already exists",
    re.IGNORECASE,
)


class PersistenceError(Exception):
    """A database write/read failed at the persistence boundary."""


class DuplicateClientOrderId(PersistenceError):
    """``orders.client_order_id`` uniqueness was violated."""

    def __init__(self, client_order_id: str | None = None) -> None:
        self.client_order_id = client_order_id
        suffix = "" if client_order_id is None else f": {client_order_id}"
        super().__init__(f"duplicate client_order_id{suffix}")


class DuplicateExchangeOrderId(PersistenceError):
    """``orders.exchange_order_id`` uniqueness was violated."""

    def __init__(self, exchange_order_id: str | None = None) -> None:
        self.exchange_order_id = exchange_order_id
        suffix = "" if exchange_order_id is None else f": {exchange_order_id}"
        super().__init__(f"duplicate exchange_order_id{suffix}")


def map_integrity_error(error: IntegrityError) -> PersistenceError:
    """Translate a unique-constraint failure into a persistence error.

    The original IntegrityError is chained by the caller (``raise ... from error``).
    """

    text = _integrity_text(error)
    constraint = _constraint_name(error, text)
    key_column, key_value = _unique_key(text)

    if constraint == "uq_orders_client_order_id" or key_column == "client_order_id":
        value = key_value if key_column == "client_order_id" else None
        return DuplicateClientOrderId(value)
    if constraint == "uq_orders_exchange_order_id" or key_column == "exchange_order_id":
        value = key_value if key_column == "exchange_order_id" else None
        return DuplicateExchangeOrderId(value)
    if constraint is not None:
        return PersistenceError(f"integrity error ({constraint})")
    return PersistenceError("integrity error")


def _constraint_name(error: IntegrityError, text: str) -> str | None:
    orig = error.orig
    if orig is not None:
        diag = getattr(orig, "diag", None)
        name = getattr(diag, "constraint_name", None)
        if isinstance(name, str) and name:
            return name
        orig_name = getattr(orig, "constraint_name", None)
        if isinstance(orig_name, str) and orig_name:
            return orig_name
    for known in (
        "uq_orders_client_order_id",
        "uq_orders_exchange_order_id",
    ):
        if known in text:
            return known
    return None


def _unique_key(text: str) -> tuple[str | None, str | None]:
    match = _KEY_ALREADY_EXISTS.search(text)
    if match is None:
        return None, None
    return match.group("column"), match.group("value")


def _integrity_text(error: IntegrityError) -> str:
    parts = [str(error)]
    orig = error.orig
    if orig is not None:
        parts.append(str(orig))
        diag = getattr(orig, "diag", None)
        if diag is not None:
            for attr in ("constraint_name", "message_primary", "message_detail"):
                value = getattr(diag, attr, None)
                if value:
                    parts.append(str(value))
    return "\n".join(parts)
