from collections.abc import Callable

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import src.db.models  # noqa: F401
from src.db.base import Base


class DatabaseSessionManager:
    def __init__(self, database_url: str) -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self._engine = create_engine(database_url, future=True, connect_args=connect_args)
        self.session_factory: Callable[[], Session] = sessionmaker(
            bind=self._engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    def create_tables(self) -> None:
        Base.metadata.create_all(self._engine)

    def dispose(self) -> None:
        self._engine.dispose()
