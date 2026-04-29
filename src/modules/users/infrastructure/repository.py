import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.modules.users.domain.models import UserCreate, UserRead, UserRole, UserUpdate
from src.modules.users.infrastructure.models import UserORM


@dataclass(slots=True)
class StoredUserCredentials:
    id: int
    password_hash: str
    role: UserRole


class SQLAlchemyUserRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def count(self) -> int:
        with self._session_factory() as session:
            total = session.scalar(select(func.count()).select_from(UserORM))
            return int(total or 0)

    def create(self, payload: UserCreate, role: UserRole) -> UserRead:
        with self._session_factory() as session:
            user = UserORM(
                name=payload.name,
                email=payload.email,
                password_hash=self._hash_password(payload.password),
                role=role.value,
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

    def get_by_id(self, id: int) -> UserRead | None:
        with self._session_factory() as session:
            user = session.get(UserORM, id)
            return self._to_read_model(user) if user else None

    def get_credentials_by_email(self, email: str) -> StoredUserCredentials | None:
        with self._session_factory() as session:
            user = session.scalar(select(UserORM).where(UserORM.email == email))
            if user is None:
                return None

            return StoredUserCredentials(
                id=user.id,
                password_hash=user.password_hash,
                role=UserRole(user.role),
            )

    def update(self, id: int, payload: UserUpdate, role: UserRole | None) -> UserRead | None:
        with self._session_factory() as session:
            user = session.get(UserORM, id)
            if user is None:
                return None

            user.name = payload.name
            user.email = payload.email
            if payload.password:
                user.password_hash = self._hash_password(payload.password)
            user.role = role.value if role else user.role
            user.cpf = payload.cpf
            user.cnpj = payload.cnpj
            user.cep = payload.cep
            user.business = payload.business
            return self._commit_and_refresh(session, user)

    def delete(self, id: int) -> bool:
        with self._session_factory() as session:
            user = session.get(UserORM, id)
            if user is None:
                return False

            session.delete(user)
            session.commit()
            return True

    def verify_password(self, plain_password: str, stored_password_hash: str) -> bool:
        try:
            salt, hashed_password = stored_password_hash.split("$", maxsplit=1)
        except ValueError:
            return False

        candidate_hash = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        ).hex()
        return secrets.compare_digest(candidate_hash, hashed_password)

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
            role=UserRole(user.role),
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
