import asyncio

from app.market_data.rate_limit import (
    RateLimitBudget,
    SlidingWindowRateLimiter,
    backoff_seconds,
)


class FakeClock:
    def __init__(self, start: float = 1_000.0) -> None:
        self.now = start
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_acquire_waits_when_window_is_full() -> None:
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(
        RateLimitBudget(max_requests=2, window_seconds=1.0),
        clock=clock,
        sleeper=clock.sleep,
    )

    async def run() -> None:
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()

    asyncio.run(run())
    assert clock.sleeps == [1.0]
    assert clock.now == 1_001.0


def test_backoff_is_deterministic_with_injected_rng() -> None:
    budget = RateLimitBudget(
        max_requests=1,
        window_seconds=1.0,
        initial_backoff_seconds=1.0,
        max_backoff_seconds=8.0,
        jitter_ratio=0.5,
    )
    first = backoff_seconds(0, budget, rng=lambda: 0.0)
    second = backoff_seconds(1, budget, rng=lambda: 1.0)
    assert first == 1.0
    assert second == 3.0
