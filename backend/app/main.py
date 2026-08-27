"""FastAPI control-plane entrypoint. Trading loop must not live in this process."""

from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from app.api.system import router as system_router
from app.config import Settings, get_settings
from app.infrastructure.logging import configure_logging, request_id_ctx

REQUEST_ID_HEADER = "X-Request-ID"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory so tests can inject settings without mutating globals."""

    resolved = settings if settings is not None else get_settings()
    configure_logging(resolved.log_level)

    app = FastAPI(
        title="neuroTrade",
        version="0.1.0",
        summary="Deterministic quant/systematic trading control plane",
    )
    app.state.settings = resolved
    app.include_router(system_router)

    @app.middleware("http")
    async def attach_request_id(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming.strip() if incoming and incoming.strip() else str(uuid4())
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    return app


app = create_app()
