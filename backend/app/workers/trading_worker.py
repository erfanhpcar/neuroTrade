"""Trading worker process. Independent from the FastAPI HTTP lifecycle.

Phase 0 is a heartbeat stub only: it does not run Strategy, Risk, or Execution,
does not place orders, and does not size positions. Default mode is PAPER.
``TRADING_MODE=FULL`` is rejected by Settings at process start.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from app.config import Settings, TradingMode, get_settings
from app.infrastructure.logging import configure_logging

logger = logging.getLogger("neurotrade.trading_worker")

DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 5.0
WorkerStatus = Literal["alive"]
WorkerService = Literal["trading-worker"]


@dataclass(frozen=True)
class WorkerHeartbeat:
    """Liveness record emitted by the worker process.

    Phase 0 writes this to structured logs only. Redis/DB heartbeat persistence
    is deferred until a readiness/status consumer exists.
    """

    timestamp: datetime
    trading_mode: TradingMode
    status: WorkerStatus
    service: WorkerService


def _utc_now() -> datetime:
    return datetime.now(UTC)


def build_heartbeat(
    settings: Settings,
    *,
    now: Callable[[], datetime] | None = None,
) -> WorkerHeartbeat:
    """Build a timezone-aware UTC heartbeat. Does not perform I/O."""

    timestamp = (now or _utc_now)()
    if timestamp.tzinfo is None:
        raise ValueError("heartbeat timestamp must be timezone-aware UTC")
    return WorkerHeartbeat(
        timestamp=timestamp.astimezone(UTC),
        trading_mode=settings.trading_mode,
        status="alive",
        service="trading-worker",
    )


def _log_heartbeat(beat: WorkerHeartbeat) -> None:
    logger.info(
        "trading-worker heartbeat service=%s mode=%s status=%s ts=%s",
        beat.service,
        beat.trading_mode.value,
        beat.status,
        beat.timestamp.isoformat(),
    )


async def run_heartbeat_loop(
    settings: Settings,
    stop_event: asyncio.Event,
    *,
    interval_seconds: float = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    emit: Callable[[WorkerHeartbeat], None] | None = None,
    now: Callable[[], datetime] | None = None,
) -> None:
    """Emit heartbeats until ``stop_event`` is set. No trading side effects."""

    if interval_seconds <= 0:
        raise ValueError("heartbeat interval must be positive")

    sink = emit if emit is not None else _log_heartbeat
    logger.info("trading-worker starting mode=%s", settings.trading_mode.value)
    try:
        while not stop_event.is_set():
            sink(build_heartbeat(settings, now=now))
            await sleep(interval_seconds)
    finally:
        logger.info("trading-worker stopped")


def _install_signal_handlers(loop: asyncio.AbstractEventLoop, stop_event: asyncio.Event) -> None:
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)


def main() -> int:
    """Entrypoint for ``python -m app.workers.trading_worker``."""

    settings = get_settings()
    configure_logging(settings.log_level)

    async def _runner() -> None:
        stop_event = asyncio.Event()
        _install_signal_handlers(asyncio.get_running_loop(), stop_event)
        await run_heartbeat_loop(settings, stop_event)

    asyncio.run(_runner())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
