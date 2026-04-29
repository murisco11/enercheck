from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.app.core.config import get_settings
from src.app.core.container import AppContainer
from src.app.core.security import AuthTokenPayload, TokenService
from src.db.session import DatabaseSessionManager
from src.integrations.ai.factory import build_ai_provider
from src.messaging.factory import build_messaging_backend
from src.modules.ai_demo.application.use_cases import (
    AIDemoService,
    EnqueueAIDemoJobUseCase,
)
from src.modules.users.application.use_cases import AuthenticatedUser, UserService
from src.modules.users.infrastructure.repository import SQLAlchemyUserRepository

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_container() -> AppContainer:
    settings = get_settings()
    db_session_manager = DatabaseSessionManager(settings.resolved_database_url)
    token_service = TokenService(
        secret_key=settings.auth_secret_key,
        expire_minutes=settings.auth_token_expire_minutes,
    )
    message_backend = build_messaging_backend(settings)
    ai_provider = build_ai_provider(settings)
    ai_demo_service = AIDemoService(ai_provider=ai_provider)
    user_repository = SQLAlchemyUserRepository(db_session_manager.session_factory)
    user_service = UserService(repository=user_repository, token_service=token_service)

    return AppContainer(
        settings=settings,
        db_session_manager=db_session_manager,
        token_service=token_service,
        ai_provider=ai_provider,
        message_publisher=message_backend.publisher,
        message_consumer=message_backend.consumer,
        ai_demo_service=ai_demo_service,
        user_service=user_service,
    )


def get_ai_demo_service() -> AIDemoService:
    return get_container().ai_demo_service


def get_enqueue_ai_demo_job_use_case() -> EnqueueAIDemoJobUseCase:
    container = get_container()
    return EnqueueAIDemoJobUseCase(publisher=container.message_publisher)


def get_user_service() -> UserService:
    return get_container().user_service


def get_token_service() -> TokenService:
    return get_container().token_service


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso ausente.",
        )

    try:
        payload: AuthTokenPayload = token_service.decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    try:
        return user_service.get_authenticated_user_by_id(int(payload.sub))
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario do token nao encontrado.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido.",
        ) from exc


def require_admin(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores.",
        )

    return current_user
