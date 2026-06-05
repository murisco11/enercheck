import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.core.enums import (
    CanalRecuperacao,
    ModoDevolucao,
    Prioridade,
    StatusItem,
    StatusRecuperacao,
)
from src.app.db.session import Base


class CasoRecuperacao(Base):
    __tablename__ = "caso_recuperacao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cliente.id"), nullable=False)
    unidade_consumidora_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("unidade_consumidora.id"), nullable=False
    )
    lote_auditoria_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lote_auditoria.id"), nullable=True
    )
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuario.id"), nullable=True
    )
    criado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    numero_caso: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[StatusRecuperacao] = mapped_column(
        SAEnum(StatusRecuperacao, name="status_recuperacao_enum", create_constraint=True),
        nullable=False,
        default=StatusRecuperacao.ABERTO,
    )
    prioridade: Mapped[Prioridade] = mapped_column(
        SAEnum(Prioridade, name="prioridade_enum", create_constraint=True),
        nullable=False,
        default=Prioridade.MEDIA,
    )
    total_estimado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    total_recuperavel: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    total_reconhecido: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    total_devolvido: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    canal_protocolo: Mapped[CanalRecuperacao | None] = mapped_column(
        SAEnum(CanalRecuperacao, name="canal_recuperacao_enum", create_constraint=True),
        nullable=True,
    )
    numero_protocolo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    protocolado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    aberto_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fechado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    itens: Mapped[list["ItemRecuperacao"]] = relationship(
        back_populates="caso", cascade="all, delete-orphan", lazy="raise"
    )

    __table_args__ = (
        Index("ix_caso_cliente", "cliente_id"),
        Index("ix_caso_uc", "unidade_consumidora_id"),
        Index("ix_caso_status", "status"),
    )


class ItemRecuperacao(Base):
    __tablename__ = "item_recuperacao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    caso_recuperacao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("caso_recuperacao.id", ondelete="CASCADE"), nullable=False
    )
    achado_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("achado.id"), nullable=False)
    fatura_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fatura.id"), nullable=False)
    valor_cobrado_a_maior: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    modo_devolucao: Mapped[ModoDevolucao | None] = mapped_column(
        SAEnum(ModoDevolucao, name="modo_devolucao_enum", create_constraint=False),
        nullable=True,
    )
    valor_recuperavel: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_reconhecido: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_devolvido: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    status: Mapped[StatusItem] = mapped_column(
        SAEnum(StatusItem, name="status_item_enum", create_constraint=True),
        nullable=False,
        default=StatusItem.ABERTO,
    )

    caso: Mapped["CasoRecuperacao"] = relationship(back_populates="itens", lazy="raise")

    __table_args__ = (
        Index("ix_item_recuperacao_caso", "caso_recuperacao_id"),
        Index("ix_item_recuperacao_achado", "achado_id"),
    )
