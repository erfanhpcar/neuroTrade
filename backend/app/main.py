"""FastAPI control-plane entrypoint.

The HTTP process is intentionally separate from the trading worker
(`app.workers.trading_worker`). Restarting this API must never start or duplicate
trading activity.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import system
from app.config import get_settings


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title="neuroTrade Control Plane",
        version="0.0.0",
        summary="Phase 0 skeleton — deterministic quant trading platform (PAPER by default).",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(system.router)
    return app


app = create_app()
