import ast
import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings, TradingMode
from app.workers.trading_worker import WorkerHeartbeat, build_heartbeat, run_heartbeat_loop

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".", 1)[0])
    return names


def test_heartbeat_uses_paper_and_timezone_aware_utc() -> None:
    settings = Settings(_env_file=None)
    ts = datetime(2026, 8, 27, 17, 30, tzinfo=UTC)
    beat = build_heartbeat(settings, now=lambda: ts)
    assert beat == WorkerHeartbeat(
        timestamp=ts,
        trading_mode=TradingMode.PAPER,
        status="alive",
        service="trading-worker",
    )
    assert beat.timestamp.tzinfo is UTC


def test_heartbeat_rejects_naive_timestamp() -> None:
    settings = Settings(_env_file=None)
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        build_heartbeat(settings, now=lambda: datetime(2026, 8, 27, 17, 30))


def test_heartbeat_loop_emits_then_stops() -> None:
    settings = Settings(_env_file=None)
    stop_event = asyncio.Event()
    emitted: list[WorkerHeartbeat] = []

    async def _sleep(_: float) -> None:
        stop_event.set()

    asyncio.run(
        run_heartbeat_loop(
            settings,
            stop_event,
            interval_seconds=0.01,
            sleep=_sleep,
            emit=emitted.append,
            now=lambda: datetime(2026, 8, 27, 17, 31, tzinfo=UTC),
        )
    )

    assert len(emitted) == 1
    assert emitted[0].trading_mode is TradingMode.PAPER
    assert emitted[0].service == "trading-worker"


def test_heartbeat_loop_skips_when_already_stopped() -> None:
    settings = Settings(_env_file=None)
    stop_event = asyncio.Event()
    stop_event.set()
    emitted: list[WorkerHeartbeat] = []

    async def _sleep(_: float) -> None:
        raise AssertionError("sleep must not be called when already stopped")

    asyncio.run(
        run_heartbeat_loop(
            settings,
            stop_event,
            interval_seconds=0.01,
            sleep=_sleep,
            emit=emitted.append,
        )
    )
    assert emitted == []


def test_heartbeat_loop_rejects_non_positive_interval() -> None:
    settings = Settings(_env_file=None)

    async def _run() -> None:
        await run_heartbeat_loop(settings, asyncio.Event(), interval_seconds=0)

    with pytest.raises(ValueError, match="positive"):
        asyncio.run(_run())


def test_worker_process_rejects_full_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRADING_MODE", "FULL")
    with pytest.raises(ValidationError, match="FULL is disabled"):
        Settings(_env_file=None)


def test_worker_module_does_not_import_fastapi_or_execution() -> None:
    imported = _imported_modules(BACKEND_ROOT / "app" / "workers" / "trading_worker.py")
    assert "fastapi" not in imported
    assert "execution" not in imported
    assert "strategies" not in imported
    assert "ccxt" not in imported


def test_control_plane_does_not_start_the_worker() -> None:
    source = (BACKEND_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "trading_worker" not in source
    assert "workers" not in source
