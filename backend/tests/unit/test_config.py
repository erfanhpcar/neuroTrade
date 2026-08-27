import pytest
from pydantic import ValidationError

from app.config import Settings, TradingMode, get_settings


def test_default_trading_mode_is_paper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRADING_MODE", raising=False)
    get_settings.cache_clear()
    settings = Settings(_env_file=None)
    assert settings.trading_mode is TradingMode.PAPER


def test_empty_trading_mode_defaults_to_paper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRADING_MODE", "")
    settings = Settings(_env_file=None)
    assert settings.trading_mode is TradingMode.PAPER


def test_semi_mode_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRADING_MODE", "SEMI")
    settings = Settings(_env_file=None)
    assert settings.trading_mode is TradingMode.SEMI


def test_invalid_trading_mode_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRADING_MODE", "LIVE")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_database_and_redis_urls_default_to_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    settings = Settings(_env_file=None)
    assert "localhost:5432" in settings.database_url
    assert settings.redis_url == "redis://localhost:6379/0"


def test_full_mode_is_rejected_until_live_readiness(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRADING_MODE", "FULL")
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert "FULL is disabled" in str(exc_info.value)
