import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.core.enums import Grupo, ModalidadeTarifaria, StatusLote, Subgrupo
from src.app.db.mixins import SoftDeleteMixin, TimestampMixin
from src.app.db.session import Base


class Distribuidora(SoftDeleteMixin, Base):
    __tablename__ = "distribuidora"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    razao_social: Mapped[str] = mapped_column(String(255), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(14), nullable=False, unique=True)
    sigla: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[str] = mapped_column(String(2), nullable=False)

    unidades_consumidoras: Mapped[list["UnidadeConsumidora"]] = relationship(
        back_populates="distribuidora",
        lazy="raise",
    )

    __table_args__ = (Index("ix_distribuidora_cnpj", "cnpj"),)


class Cliente(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "cliente"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    razao_social: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_fantasia: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cnpj: Mapped[str] = mapped_column(String(14), nullable=False, unique=True)

    unidades_consumidoras: Mapped[list["UnidadeConsumidora"]] = relationship(
        back_populates="cliente",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    acessos: Mapped[list["AcessoCliente"]] = relationship(
        back_populates="cliente",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    __table_args__ = (Index("ix_cliente_cnpj", "cnpj"),)


class AcessoCliente(Base):
    __tablename__ = "acesso_cliente"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cliente.id", ondelete="CASCADE"), nullable=False
    )
    pode_editar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    cliente: Mapped["Cliente"] = relationship(back_populates="acessos", lazy="raise")

    __table_args__ = (
        UniqueConstraint("usuario_id", "cliente_id", name="uq_acesso_cliente_usuario_cliente"),
        Index("ix_acesso_cliente_usuario", "usuario_id"),
        Index("ix_acesso_cliente_cliente", "cliente_id"),
    )


class UnidadeConsumidora(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "unidade_consumidora"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cliente.id"), nullable=False)
    distribuidora_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("distribuidora.id"), nullable=False
    )
    codigo_instalacao: Mapped[str] = mapped_column(String(50), nullable=False)
    codigo_cliente: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grupo: Mapped[Grupo] = mapped_column(
        SAEnum(Grupo, name="grupo_enum", create_constraint=True), nullable=False
    )
    subgrupo: Mapped[Subgrupo] = mapped_column(
        SAEnum(Subgrupo, name="subgrupo_enum", create_constraint=True), nullable=False
    )
    modalidade: Mapped[ModalidadeTarifaria] = mapped_column(
        SAEnum(ModalidadeTarifaria, name="modalidade_tarifaria_enum", create_constraint=True),
        nullable=False,
    )
    tarifa_social: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cidade: Mapped[str] = mapped_column(String(100), nullable=False)
    estado: Mapped[str] = mapped_column(String(2), nullable=False)

    cliente: Mapped["Cliente"] = relationship(back_populates="unidades_consumidoras", lazy="raise")
    distribuidora: Mapped["Distribuidora"] = relationship(
        back_populates="unidades_consumidoras", lazy="raise"
    )
    lotes: Mapped[list["LoteAuditoria"]] = relationship(
        back_populates="unidade_consumidora",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    __table_args__ = (
        UniqueConstraint(
            "distribuidora_id", "codigo_instalacao", name="uq_uc_distribuidora_instalacao"
        ),
        Index("ix_uc_cliente", "cliente_id"),
        Index("ix_uc_distribuidora", "distribuidora_id"),
    )


class LoteAuditoria(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "lote_auditoria"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    unidade_consumidora_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("unidade_consumidora.id"), nullable=False
    )
    criado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    rotulo: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[StatusLote] = mapped_column(
        SAEnum(StatusLote, name="status_lote_enum", create_constraint=True),
        nullable=False,
        default=StatusLote.PENDENTE,
    )
    competencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    competencia_fim: Mapped[date] = mapped_column(Date, nullable=False)

    unidade_consumidora: Mapped["UnidadeConsumidora"] = relationship(
        back_populates="lotes", lazy="raise"
    )

    __table_args__ = (
        Index("ix_lote_uc", "unidade_consumidora_id"),
        Index("ix_lote_criado_por", "criado_por_id"),
    )
