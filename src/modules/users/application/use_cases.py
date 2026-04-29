from dataclasses import dataclass

from src.app.core.security import TokenService
from src.modules.users.domain.models import (
    AuthTokenResponse,
    LoginRequest,
    UserCreate,
    UserRead,
    UserRole,
    UserUpdate,
)
from src.modules.users.infrastructure.repository import SQLAlchemyUserRepository


@dataclass(slots=True)
class AuthenticatedUser:
    id: int
    email: str
    name: str
    role: str


class UserService:
    def __init__(self, repository: SQLAlchemyUserRepository, token_service: TokenService) -> None:
        self._repository = repository
        self._token_service = token_service

    def create_user(self, payload: UserCreate) -> UserRead:
        role = UserRole.ADMIN if self._repository.count() == 0 else UserRole.USER
        return self._repository.create(payload, role=role)

    def login(self, payload: LoginRequest) -> AuthTokenResponse:
        credentials = self._repository.get_credentials_by_email(payload.email)
        if credentials is None or not self._repository.verify_password(
            payload.password,
            credentials.password_hash,
        ):
            raise ValueError("Email ou senha invalidos.")

        user = self.get_user(credentials.id)
        token = self._token_service.create_token(subject=str(user.id), role=user.role.value)
        return AuthTokenResponse(access_token=token, user=user)

    def list_users(self) -> list[UserRead]:
        return self._repository.list()

    def get_user(self, id: int) -> UserRead:
        user = self._repository.get_by_id(id)
        if user is None:
            raise LookupError("Usuario nao encontrado.")
        return user

    def get_authenticated_user_by_id(self, id: int) -> AuthenticatedUser:
        user = self.get_user(id)
        return AuthenticatedUser(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role.value,
        )

    def update_user(
        self,
        id: int,
        payload: UserUpdate,
        actor: AuthenticatedUser,
    ) -> UserRead:
        if actor.role != UserRole.ADMIN.value and actor.id != id:
            raise PermissionError("Voce nao pode alterar outro usuario.")

        next_role = payload.role if actor.role == UserRole.ADMIN.value else None
        user = self._repository.update(id, payload, role=next_role)
        if user is None:
            raise LookupError("Usuario nao encontrado.")
        return user

    def delete_user(self, id: int, actor: AuthenticatedUser) -> None:
        if actor.role != UserRole.ADMIN.value and actor.id != id:
            raise PermissionError("Voce nao pode remover outro usuario.")

        deleted = self._repository.delete(id)
        if not deleted:
            raise LookupError("Usuario nao encontrado.")
