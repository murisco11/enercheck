from fastapi import APIRouter

from src.app.api.v1.health import router as health_router
from src.app.domains.auditoria.router import (
    achados_router,
    fatura_validacoes_router,
    validacoes_router,
)
from src.app.domains.auth.router import router as auth_router
from src.app.domains.clientes.router import (
    clientes_router,
    distribuidoras_router,
    lotes_router,
)
from src.app.domains.documental.router import router as documental_router
from src.app.domains.faturas.router import router as faturas_router
from src.app.domains.recuperacao.router import router as recuperacao_router
from src.app.domains.regulatorio.router import router as regulatorio_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router, prefix="/auth")
api_router.include_router(clientes_router, prefix="/clientes")
api_router.include_router(distribuidoras_router, prefix="/distribuidoras")
api_router.include_router(lotes_router, prefix="/lotes")
api_router.include_router(documental_router, prefix="/documental")
api_router.include_router(faturas_router, prefix="/faturas")
api_router.include_router(fatura_validacoes_router, prefix="/faturas")
api_router.include_router(validacoes_router, prefix="/validacoes")
api_router.include_router(achados_router, prefix="/achados")
api_router.include_router(regulatorio_router, prefix="/regulatorio", tags=["regulatorio"])
api_router.include_router(recuperacao_router, prefix="/recuperacao")
