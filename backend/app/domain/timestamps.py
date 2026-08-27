"""UTC timestamp helpers for domain and persistence boundaries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.errors import InvalidTimestamp

UTC = UTC


def require_utc(value: datetime, *, field: str) -> datetime:
    """Accept only timezone-aware timestamps with a zero UTC offset."""

    if not isinstance(value, datetime):
        raise InvalidTimestamp(f"{field} must be datetime, got {type(value).__name__}")
    if value.tzinfo is None:
        raise InvalidTimestamp(f"{field} must be timezone-aware UTC, got naive datetime")
    offset = value.utcoffset()
    if offset is None or offset != timedelta(0):
        raise InvalidTimestamp(f"{field} must be UTC, got offset {offset}")
    return value
