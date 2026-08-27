"""Configuration tests.

The most important invariant in Phase 0: the system defaults to ``PAPER`` and never
implicitly selects live trading.
"""

from __future__ import annotations

import pytest

from app.config import Settings
from app.domain.modes import TradingMode


def test_trading_mode_defaults_to_paper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRADING_MODE", raising=False)
    settings = Settings(_env_file=None)
    assert settings.trading_mode is TradingMode.PAPER


def test_trading_mode_reads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRADING_MODE", "SEMI")
    settings = Settings(_env_file=None)
    assert settings.trading_mode is TradingMode.SEMI


def test_invalid_trading_mode_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRADING_MODE", "TURBO")
    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_asyncpg_dsn_strips_sqlalchemy_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:pass@host:5432/db",
    )
    settings = Settings(_env_file=None)
    assert settings.asyncpg_dsn == "postgresql://user:pass@host:5432/db"
