from src.modules.users.domain.models import UserCreate, UserRead, UserUpdate
from src.modules.users.infrastructure.repository import SQLAlchemyUserRepository


class UserService:
    def __init__(self, repository: SQLAlchemyUserRepository) -> None:
        self._repository = repository

    def create_user(self, payload: UserCreate) -> UserRead:
        return self._repository.create(payload)

    def list_users(self) -> list[UserRead]:
        return self._repository.list()

    def get_user(self, user_id: int) -> UserRead:
        user = self._repository.get_by_id(user_id)
        if user is None:
            raise LookupError("Usuario nao encontrado.")
        return user

    def update_user(self, user_id: int, payload: UserUpdate) -> UserRead:
        user = self._repository.update(user_id, payload)
        if user is None:
            raise LookupError("Usuario nao encontrado.")
        return user

    def delete_user(self, user_id: int) -> None:
        deleted = self._repository.delete(user_id)
        if not deleted:
            raise LookupError("Usuario nao encontrado.")
