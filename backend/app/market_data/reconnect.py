"""WebSocket reconnect policy. HTTP-free so contract tests need no network."""

from __future__ import annotations

from dataclasses import dataclass

from app.market_data.errors import MarketDataError
from app.market_data.rate_limit import UnitIntervalRng, exponential_backoff_seconds


@dataclass(frozen=True)
class ReconnectPolicy:
    """Bounded exponential backoff for a dropped public market-data stream.

    ``max_attempts`` is the number of connection attempts. ``None`` means the
    stream keeps retrying until the caller stops it. This is reconnect policy
    only; it does not retry REST ``create_order``.
    """

    initial_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 60.0
    jitter_ratio: float = 0.2
    max_attempts: int | None = None

    def __post_init__(self) -> None:
        if self.initial_backoff_seconds <= 0:
            raise MarketDataError("initial_backoff_seconds must be > 0")
        if self.max_backoff_seconds < self.initial_backoff_seconds:
            raise MarketDataError("max_backoff_seconds must be >= initial_backoff_seconds")
        if not 0 <= self.jitter_ratio <= 1:
            raise MarketDataError("jitter_ratio must be between 0 and 1 inclusive")
        if self.max_attempts is not None and self.max_attempts < 1:
            raise MarketDataError("max_attempts must be >= 1 when set")


DEFAULT_WS_RECONNECT = ReconnectPolicy(
    initial_backoff_seconds=1.0,
    max_backoff_seconds=60.0,
    jitter_ratio=0.2,
    max_attempts=None,
)


def reconnect_backoff_seconds(
    attempt: int,
    policy: ReconnectPolicy,
    rng: UnitIntervalRng,
) -> float:
    """Return sleep before the next reconnect. ``attempt`` is 0-based."""

    return exponential_backoff_seconds(
        attempt,
        initial_seconds=policy.initial_backoff_seconds,
        max_seconds=policy.max_backoff_seconds,
        jitter_ratio=policy.jitter_ratio,
        rng=rng,
    )
