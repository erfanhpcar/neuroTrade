"""Per-endpoint request budget with exponential backoff.

Rate limits are configured per adapter, not as one global hardcoded number.
This module is HTTP-free so contract tests can exercise it without httpx.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.market_data.errors import MarketDataError

Clock = Callable[[], float]
AsyncSleeper = Callable[[float], Awaitable[None]]
UnitIntervalRng = Callable[[], float]


@dataclass(frozen=True)
class RateLimitBudget:
    """Sliding-window budget for one venue endpoint.

    ``max_requests`` / ``window_seconds`` is the configured ceiling for this
    adapter. Retry/backoff fields apply after 429/403/retCode 10006 responses.
    """

    max_requests: int
    window_seconds: float
    max_retries: int = 4
    initial_backoff_seconds: float = 0.5
    max_backoff_seconds: float = 8.0
    jitter_ratio: float = 0.2

    def __post_init__(self) -> None:
        if self.max_requests < 1:
            raise MarketDataError("max_requests must be >= 1")
        if self.window_seconds <= 0:
            raise MarketDataError("window_seconds must be > 0")
        if self.max_retries < 0:
            raise MarketDataError("max_retries must be >= 0")
        if self.initial_backoff_seconds <= 0:
            raise MarketDataError("initial_backoff_seconds must be > 0")
        if self.max_backoff_seconds < self.initial_backoff_seconds:
            raise MarketDataError("max_backoff_seconds must be >= initial_backoff_seconds")
        if not 0 <= self.jitter_ratio <= 1:
            raise MarketDataError("jitter_ratio must be between 0 and 1 inclusive")


# Official Bybit HTTP IP ceiling: 600 requests / 5 seconds across api.bybit.com.
# https://bybit-exchange.github.io/docs/v5/rate-limit
BYBIT_HTTP_IP_MAX_REQUESTS = 600
BYBIT_HTTP_IP_WINDOW_SECONDS = 5.0

# Conservative GET /v5/market/kline budget. Stays well below the shared IP ceiling.
# Callers may raise this, but not above the documented IP limit.
DEFAULT_BYBIT_KLINE_BUDGET = RateLimitBudget(
    max_requests=10,
    window_seconds=1.0,
    max_retries=4,
    initial_backoff_seconds=0.5,
    max_backoff_seconds=8.0,
    jitter_ratio=0.2,
)


def backoff_seconds(attempt: int, budget: RateLimitBudget, rng: UnitIntervalRng) -> float:
    """Return sleep time for a 0-based retry attempt, with bounded jitter."""

    if attempt < 0:
        raise MarketDataError("attempt must be >= 0")
    base = min(
        budget.max_backoff_seconds,
        budget.initial_backoff_seconds * (2**attempt),
    )
    sample = float(rng())
    jitter = base * budget.jitter_ratio * sample
    return float(base + jitter)


class SlidingWindowRateLimiter:
    """Allow at most ``budget.max_requests`` acquires per ``window_seconds``."""

    def __init__(
        self,
        budget: RateLimitBudget,
        *,
        clock: Clock | None = None,
        sleeper: AsyncSleeper | None = None,
    ) -> None:
        self._budget = budget
        self._clock: Clock = clock or _monotonic
        self._sleeper: AsyncSleeper = sleeper or _asyncio_sleep
        self._stamps: list[float] = []

    @property
    def budget(self) -> RateLimitBudget:
        return self._budget

    async def acquire(self) -> None:
        """Block until the current window has a free slot, then consume it."""

        while True:
            now = self._clock()
            window_start = now - self._budget.window_seconds
            self._stamps = [stamp for stamp in self._stamps if stamp > window_start]
            if len(self._stamps) < self._budget.max_requests:
                self._stamps.append(now)
                return
            oldest = self._stamps[0]
            sleep_for = oldest + self._budget.window_seconds - now
            if sleep_for > 0:
                await self.sleep(sleep_for)

    async def sleep(self, seconds: float) -> None:
        """Sleep using the injected sleeper. Used for retry backoff as well."""

        if seconds > 0:
            await self._sleeper(seconds)


def _monotonic() -> float:
    return time.monotonic()


async def _asyncio_sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


def default_rng() -> UnitIntervalRng:
    """Return a 0..1 sampler. Tests should inject a deterministic rng."""

    def _sample() -> float:
        return float(random.random())

    return _sample
