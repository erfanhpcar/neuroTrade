"""System endpoints: liveness, dependency health, and operational status.

Contract source: ``docs/10_REST_API.md`` (System section). Phase 0 implements the
read-only endpoints (`/api/health`, `/api/system/status`); mutating operator
commands (mode change, HALT, FLATTEN_ALL) arrive in later phases.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.infrastructure.health import check_postgres, check_redis

router = APIRouter(prefix="/api", tags=["system"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


class DependencyHealth(BaseModel):
    postgres: bool
    redis: bool


class HealthResponse(BaseModel):
    status: str
    trading_mode: str
    dependencies: DependencyHealth


class SystemStatusResponse(BaseModel):
    trading_mode: str
    app_env: str
    market_data_provider: str
    default_symbol: str
    default_timeframe: str


@router.get("/health", response_model=HealthResponse)
async def health(settings: SettingsDep) -> HealthResponse:
    """Report process liveness plus best-effort dependency connectivity."""
    postgres_ok = await check_postgres(settings)
    redis_ok = await check_redis(settings)
    overall = "ok" if postgres_ok and redis_ok else "degraded"
    return HealthResponse(
        status=overall,
        trading_mode=settings.trading_mode.value,
        dependencies=DependencyHealth(postgres=postgres_ok, redis=redis_ok),
    )


@router.get("/system/status", response_model=SystemStatusResponse)
async def system_status(settings: SettingsDep) -> SystemStatusResponse:
    """Return current operational configuration for the dashboard."""
    return SystemStatusResponse(
        trading_mode=settings.trading_mode.value,
        app_env=settings.app_env,
        market_data_provider=settings.market_data_provider,
        default_symbol=settings.default_symbol,
        default_timeframe=settings.default_timeframe,
    )
