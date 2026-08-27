"""Shared scalar field checks for domain entities."""

from __future__ import annotations

from uuid import UUID

from app.domain.errors import DomainError


def require_text(value: str, *, field: str) -> str:
    if not isinstance(value, str):
        raise DomainError(f"{field} must be str, got {type(value).__name__}")
    text = value.strip()
    if not text:
        raise DomainError(f"{field} must be a non-empty string")
    if text != value:
        raise DomainError(f"{field} must not include surrounding whitespace")
    return text


def require_symbol(value: str) -> str:
    return require_text(value, field="symbol")


def require_timeframe(value: str) -> str:
    return require_text(value, field="timeframe")


def require_client_order_id(value: str) -> str:
    """Identity used for exchange idempotency. Uniqueness is enforced at persistence."""

    text = require_text(value, field="client_order_id")
    if any(ch.isspace() for ch in text):
        raise DomainError("client_order_id must not contain whitespace")
    return text


def require_uuid(value: UUID, *, field: str) -> UUID:
    if not isinstance(value, UUID):
        raise DomainError(f"{field} must be UUID, got {type(value).__name__}")
    return value
