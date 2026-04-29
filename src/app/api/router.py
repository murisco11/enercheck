from fastapi import APIRouter

from src.app.api.routes.ai_demo import router as ai_demo_router
from src.app.api.routes.health import router as health_router
from src.app.api.routes.users import router as users_router


def build_api_router() -> APIRouter:
    router = APIRouter()
    router.include_router(health_router)
    router.include_router(ai_demo_router)
    router.include_router(users_router)
    return router
