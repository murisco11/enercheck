from fastapi import APIRouter

from src.app.api.v1.health import router as health_router
from src.app.domains.auth.router import router as auth_router
from src.app.domains.clientes.router import (
    clientes_router,
    distribuidoras_router,
    lotes_router,
)
from src.app.domains.regulatorio.router import router as regulatorio_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router, prefix="/auth")
api_router.include_router(clientes_router, prefix="/clientes")
api_router.include_router(distribuidoras_router, prefix="/distribuidoras")
api_router.include_router(lotes_router, prefix="/lotes")
api_router.include_router(regulatorio_router, prefix="/regulatorio", tags=["regulatorio"])
