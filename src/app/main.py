import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.app.api.v1.dependencies import get_session_manager
from src.app.api.v1.router import api_router
from src.app.core.config import get_settings
from src.app.core.exceptions import (
    AcessoNegadoError,
    ConflitoDuplicidadeError,
    CredenciaisInvalidasError,
    IntegrationError,
    NaoEncontradoError,
    RegraVioladaError,
)
from src.app.core.logging import configure_logging
from src.app.core.middleware import RequestContextMiddleware
from src.app.core.openapi_selects import configurar_selects_openapi

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    mgr = get_session_manager()
    mgr.create_tables()
    try:
        yield
    finally:
        mgr.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)
app.include_router(api_router)
configurar_selects_openapi(app)


@app.exception_handler(NaoEncontradoError)
async def handle_nao_encontrado(_: Request, exc: NaoEncontradoError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflitoDuplicidadeError)
async def handle_conflito(_: Request, exc: ConflitoDuplicidadeError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(RegraVioladaError)
async def handle_regra(_: Request, exc: RegraVioladaError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(AcessoNegadoError)
async def handle_acesso_negado(_: Request, exc: AcessoNegadoError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(CredenciaisInvalidasError)
async def handle_credenciais(_: Request, exc: CredenciaisInvalidasError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})


@app.exception_handler(IntegrationError)
async def handle_integration(_: Request, exc: IntegrationError) -> JSONResponse:
    logger.exception("integration.error: %s", exc)
    return JSONResponse(
        status_code=502,
        content={"detail": "Falha ao processar integração externa."},
    )
