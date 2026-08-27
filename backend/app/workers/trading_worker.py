"""Trading worker (Phase 0 skeleton).

This process owns the trading loop lifecycle. In Phase 0 it does not trade: it
runs a heartbeat that publishes liveness to Redis so the control plane and
dashboard can detect a stale worker. Strategy/Risk/Execution engines are added in
later phases and must always keep ``PAPER`` as the safe default.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import signal
from datetime import UTC, datetime

import redis.asyncio as redis

from app.config import Settings, get_settings

logger = logging.getLogger("neurotrade.trading_worker")

HEARTBEAT_KEY = "neurotrade:worker:heartbeat"
HEARTBEAT_INTERVAL_SECONDS = 5
HEARTBEAT_TTL_SECONDS = 15


async def _publish_heartbeat(client: redis.Redis, settings: Settings) -> None:
    """Write a single heartbeat record with a TTL so staleness is detectable."""
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "trading_mode": settings.trading_mode.value,
        "status": "alive",
    }
    await client.set(HEARTBEAT_KEY, json.dumps(payload), ex=HEARTBEAT_TTL_SECONDS)


async def run_worker(stop_event: asyncio.Event, settings: Settings | None = None) -> None:
    """Run the heartbeat loop until ``stop_event`` is set."""
    settings = settings or get_settings()
    client = redis.from_url(settings.redis_url)
    logger.info("trading-worker starting in %s mode", settings.trading_mode.value)
    try:
        while not stop_event.is_set():
            try:
                await _publish_heartbeat(client, settings)
                logger.info("heartbeat published (mode=%s)", settings.trading_mode.value)
            except (OSError, redis.RedisError) as exc:
                logger.warning("heartbeat publish failed: %s", exc)
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(stop_event.wait(), timeout=HEARTBEAT_INTERVAL_SECONDS)
    finally:
        await client.aclose()
        logger.info("trading-worker stopped")


def _install_signal_handlers(loop: asyncio.AbstractEventLoop, stop_event: asyncio.Event) -> None:
    """Request a graceful shutdown on SIGINT/SIGTERM."""
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)


def main() -> None:
    """Entrypoint for ``python -m app.workers.trading_worker``."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    async def _runner() -> None:
        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()
        _install_signal_handlers(loop, stop_event)
        await run_worker(stop_event)

    asyncio.run(_runner())


if __name__ == "__main__":
    main()
