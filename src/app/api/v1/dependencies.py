import uuid
from collections.abc import Generator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.app.core.config import get_settings
from src.app.core.enums import PapelUsuario
from src.app.core.exceptions import CredenciaisInvalidasError, NaoEncontradoError
from src.app.core.security import AuthTokenPayload, TokenService
from src.app.db.session import DatabaseSessionManager
from src.app.domains.auth.service import UsuarioAutenticado, UsuarioService

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_session_manager() -> DatabaseSessionManager:
    return DatabaseSessionManager(get_settings().resolved_database_url)


@lru_cache
def get_token_service() -> TokenService:
    settings = get_settings()
    return TokenService(
        secret_key=settings.auth_secret_key,
        expire_minutes=settings.auth_token_expire_minutes,
    )


def get_db() -> Generator[Session, None, None]:
    yield from get_session_manager().get_db()


DbDep = Annotated[Session, Depends(get_db)]


def get_usuario_service(db: DbDep) -> UsuarioService:
    return UsuarioService(db=db, token_service=get_token_service())


UsuarioServiceDep = Annotated[UsuarioService, Depends(get_usuario_service)]


def get_usuario_atual(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbDep,
) -> UsuarioAutenticado:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso ausente.",
        )
    try:
        payload: AuthTokenPayload = get_token_service().decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    try:
        return UsuarioService(db=db, token_service=get_token_service()).obter_autenticado(
            uuid.UUID(payload.sub)
        )
    except (LookupError, ValueError, NaoEncontradoError, CredenciaisInvalidasError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc) or "Usuário do token não encontrado.",
        ) from exc


UsuarioAtualDep = Annotated[UsuarioAutenticado, Depends(get_usuario_atual)]


def requer_papel(*papeis: PapelUsuario):
    def verificar(usuario: UsuarioAtualDep) -> UsuarioAutenticado:
        if PapelUsuario(usuario.papel) not in papeis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso restrito.",
            )
        return usuario

    return verificar
