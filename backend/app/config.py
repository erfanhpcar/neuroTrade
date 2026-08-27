"""Application configuration.

Configuration is validated at the process boundary with Pydantic settings. The
trading mode defaults to ``PAPER`` and must never implicitly fall back to live
execution.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.modes import TradingMode


class Settings(BaseSettings):
    """Process configuration loaded from the environment.

    Names mirror ``.env.example`` and ``docs/14_DOCKER_DEPLOYMENT.md``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")

    # Safe default: never live trading unless deliberately promoted.
    trading_mode: TradingMode = Field(default=TradingMode.PAPER, alias="TRADING_MODE")

    database_url: str = Field(
        default="postgresql://neurotrade:neurotrade@localhost:5432/neurotrade",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    market_data_provider: str = Field(default="bybit", alias="MARKET_DATA_PROVIDER")
    default_symbol: str = Field(default="BTC/USDT", alias="DEFAULT_SYMBOL")
    default_timeframe: str = Field(default="4h", alias="DEFAULT_TIMEFRAME")

    # CORS origin for the local dashboard.
    frontend_origin: str = Field(default="http://localhost:3000", alias="FRONTEND_ORIGIN")

    @property
    def asyncpg_dsn(self) -> str:
        """Return a DSN that ``asyncpg`` accepts (no SQLAlchemy driver suffix)."""
        dsn = self.database_url
        if "+asyncpg" in dsn:
            dsn = dsn.replace("+asyncpg", "")
        return dsn


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for the current process."""
    return Settings()
