import hashlib
import secrets
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.modules.users.domain.models import UserCreate, UserRead, UserUpdate
from src.modules.users.infrastructure.models import UserORM


class SQLAlchemyUserRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def create(self, payload: UserCreate) -> UserRead:
        with self._session_factory() as session:
            user = UserORM(
                name=payload.name,
                email=payload.email,
                password_hash=self._hash_password(payload.password),
                cpf=payload.cpf,
                cnpj=payload.cnpj,
                cep=payload.cep,
                business=payload.business,
            )
            session.add(user)
            return self._commit_and_refresh(session, user)

    def list(self) -> list[UserRead]:
        with self._session_factory() as session:
            users = session.scalars(select(UserORM).order_by(UserORM.id)).all()
            return [self._to_read_model(user) for user in users]

    def get_by_id(self, user_id: int) -> UserRead | None:
        with self._session_factory() as session:
            user = session.get(UserORM, user_id)
            return self._to_read_model(user) if user else None

    def update(self, user_id: int, payload: UserUpdate) -> UserRead | None:
        with self._session_factory() as session:
            user = session.get(UserORM, user_id)
            if user is None:
                return None

            user.name = payload.name
            user.email = payload.email
            user.password_hash = self._hash_password(payload.password)
            user.cpf = payload.cpf
            user.cnpj = payload.cnpj
            user.cep = payload.cep
            user.business = payload.business
            return self._commit_and_refresh(session, user)

    def delete(self, user_id: int) -> bool:
        with self._session_factory() as session:
            user = session.get(UserORM, user_id)
            if user is None:
                return False

            session.delete(user)
            session.commit()
            return True

    def _commit_and_refresh(self, session: Session, user: UserORM) -> UserRead:
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("Ja existe um usuario com este email.") from exc

        session.refresh(user)
        return self._to_read_model(user)

    @staticmethod
    def _to_read_model(user: UserORM) -> UserRead:
        return UserRead(
            id=user.id,
            name=user.name,
            email=user.email,
            cpf=user.cpf,
            cnpj=user.cnpj,
            cep=user.cep,
            business=user.business,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        )
        return f"{salt}${hashed.hex()}"
