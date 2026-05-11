from datetime import datetime

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class TimestampMixin:
    @declared_attr
    def criado_em(cls) -> Mapped[datetime]:
        return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @declared_attr
    def atualizado_em(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )


class SoftDeleteMixin:
    @declared_attr
    def ativo(cls) -> Mapped[bool]:
        return mapped_column(Boolean, nullable=False, default=True, server_default="true")
