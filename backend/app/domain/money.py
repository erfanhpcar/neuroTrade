"""Decimal helpers for executable and persisted financial values.

Binary floats are rejected. Callers must pass ``str``, ``int``, or ``Decimal``.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TypeAlias

from app.domain.errors import InvalidFinancialValue

FinancialInput: TypeAlias = Decimal | int | str


def parse_decimal(value: object, *, field: str) -> Decimal:
    """Return a finite Decimal. Never constructs Decimal from a binary float."""

    if isinstance(value, bool) or value is None:
        raise InvalidFinancialValue(f"{field} must be a finite decimal, got {type(value).__name__}")
    if isinstance(value, float):
        raise InvalidFinancialValue(
            f"{field} must not be constructed from a binary float; pass str, int, or Decimal"
        )
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, int):
        parsed = Decimal(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise InvalidFinancialValue(f"{field} must be a non-empty decimal string")
        try:
            parsed = Decimal(text)
        except InvalidOperation as exc:
            raise InvalidFinancialValue(f"{field} is not a valid decimal: {value!r}") from exc
    else:
        raise InvalidFinancialValue(
            f"{field} must be str, int, or Decimal, got {type(value).__name__}"
        )

    if not parsed.is_finite():
        raise InvalidFinancialValue(f"{field} must be a finite decimal, got {parsed}")
    return parsed


def require_positive_decimal(value: object, *, field: str) -> Decimal:
    parsed = parse_decimal(value, field=field)
    if parsed <= 0:
        raise InvalidFinancialValue(f"{field} must be > 0, got {parsed}")
    return parsed


def require_non_negative_decimal(value: object, *, field: str) -> Decimal:
    parsed = parse_decimal(value, field=field)
    if parsed < 0:
        raise InvalidFinancialValue(f"{field} must be >= 0, got {parsed}")
    return parsed


def decimal_to_text(value: Decimal) -> str:
    """Serialize a finite Decimal without exponent notation for JSON/DB round-trips."""

    parsed = parse_decimal(value, field="value")
    return format(parsed, "f")


def decimal_from_text(value: str, *, field: str) -> Decimal:
    """Deserialize a previously serialized financial value."""

    return parse_decimal(value, field=field)
