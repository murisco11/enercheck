import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.app.api.router import build_api_router
from src.app.core.config import get_settings
from src.app.core.exceptions import IntegrationError
from src.app.core.logging import configure_logging
from src.app.core.middleware import RequestContextMiddleware
from src.app.dependencies import get_container

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    container = get_container()
    container.db_session_manager.create_tables()
    try:
        yield
    finally:
        container.db_session_manager.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)
app.include_router(build_api_router())


@app.exception_handler(IntegrationError)
async def integration_error_handler(_: Request, exc: IntegrationError) -> JSONResponse:
    logger.exception("integration.error: %s", exc)
    return JSONResponse(
        status_code=502,
        content={"detail": "Falha ao processar integracao externa."},
    )
