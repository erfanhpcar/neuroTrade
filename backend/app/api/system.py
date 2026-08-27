"""System control-plane routes. Phase 0 exposes liveness only."""

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.config import Settings, TradingMode

router = APIRouter(prefix="/api", tags=["system"])


class HealthResponse(BaseModel):
    """Liveness payload for ``GET /api/health``. Does not check Postgres/Redis yet."""

    status: Literal["ok"]
    service: Literal["control-plane"]
    trading_mode: TradingMode
    app_env: str


@router.get("/health", response_model=HealthResponse)
def get_health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    if not isinstance(settings, Settings):
        raise RuntimeError("control-plane settings are not configured")
    return HealthResponse(
        status="ok",
        service="control-plane",
        trading_mode=settings.trading_mode,
        app_env=settings.app_env,
    )
