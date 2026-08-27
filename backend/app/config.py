"""Process configuration. Defaults are safe for local development and tests."""

from enum import StrEnum
from functools import lru_cache
from typing import Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingMode(StrEnum):
    """Approved operational modes from docs/01_ARCH_OVERVIEW.md."""

    PAPER = "PAPER"
    SEMI = "SEMI"
    FULL = "FULL"


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables.

    ``TRADING_MODE=FULL`` is rejected until Phase 10 live-readiness gates exist.
    Missing or empty mode falls back to ``PAPER``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    trading_mode: TradingMode = TradingMode.PAPER
    log_level: str = "INFO"

    @field_validator("trading_mode", mode="before")
    @classmethod
    def empty_mode_defaults_to_paper(cls, value: object) -> object:
        if value is None or value == "":
            return TradingMode.PAPER
        return value

    @model_validator(mode="after")
    def reject_full_until_live_readiness(self) -> Self:
        if self.trading_mode is TradingMode.FULL:
            raise ValueError(
                "TRADING_MODE=FULL is disabled until Phase 10 live readiness. "
                "Use PAPER (default) or SEMI."
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return process-wide settings. Tests must call ``cache_clear()`` when mutating env."""

    return Settings()
