from collections.abc import Callable, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


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
        from sqlalchemy import text

        import src.app.db.base  # noqa: F401 — registra todos os models para o Alembic

        is_postgres = self._engine.dialect.name == "postgresql"
        if is_postgres:
            with self._engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()

        Base.metadata.create_all(self._engine)

        if is_postgres:
            with self._engine.connect() as conn:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_chunk_embedding_hnsw
                    ON chunk_regulatorio
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
                """))
                conn.commit()

    def get_db(self) -> Generator[Session, None, None]:
        with self.session_factory() as session:
            yield session

    def dispose(self) -> None:
        self._engine.dispose()
