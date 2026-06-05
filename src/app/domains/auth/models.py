import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.app.core.enums import PapelUsuario
from src.app.db.mixins import SoftDeleteMixin, TimestampMixin
from src.app.db.session import Base


class Usuario(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    papel: Mapped[PapelUsuario] = mapped_column(
        SAEnum(PapelUsuario, name="papel_usuario_enum", create_constraint=True),
        nullable=False,
    )
