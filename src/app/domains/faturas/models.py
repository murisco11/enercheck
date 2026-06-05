import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.core.enums import (
    Bandeira,
    BaseLeitura,
    ModalidadeTarifaria,
    PostoHorario,
    TipoItem,
    TipoTributo,
)
from src.app.db.session import Base


class Fatura(Base):
    __tablename__ = "fatura"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    unidade_consumidora_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("unidade_consumidora.id"), nullable=False
    )
    documento_bruto_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documento_bruto.id"), nullable=True
    )
    lote_auditoria_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lote_auditoria.id"), nullable=True
    )
    numero_nota: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chave_acesso: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    competencia: Mapped[str] = mapped_column(String(7), nullable=False)
    data_emissao: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_vencimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_leitura_anterior: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_leitura_atual: Mapped[date | None] = mapped_column(Date, nullable=True)
    dias_faturados: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    bandeira: Mapped[Bandeira | None] = mapped_column(
        SAEnum(Bandeira, name="bandeira_enum", create_constraint=False), nullable=True
    )
    valor_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    modalidade: Mapped[ModalidadeTarifaria] = mapped_column(
        SAEnum(ModalidadeTarifaria, name="modalidade_tarifaria_enum", create_constraint=False),
        nullable=False,
    )
    base_leitura: Mapped[BaseLeitura] = mapped_column(
        SAEnum(BaseLeitura, name="base_leitura_enum", create_constraint=True),
        nullable=False,
        default=BaseLeitura.REAL,
    )
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    medidas: Mapped[list["MedidaFatura"]] = relationship(
        back_populates="fatura", cascade="all, delete-orphan", lazy="raise"
    )
    itens: Mapped[list["ItemFatura"]] = relationship(
        back_populates="fatura", cascade="all, delete-orphan", lazy="raise"
    )
    tributos: Mapped[list["TributoFatura"]] = relationship(
        back_populates="fatura", cascade="all, delete-orphan", lazy="raise"
    )

    __table_args__ = (
        Index("ix_fatura_uc", "unidade_consumidora_id"),
        Index("ix_fatura_lote", "lote_auditoria_id"),
        Index("ix_fatura_competencia", "competencia"),
    )


class MedidaFatura(Base):
    __tablename__ = "medida_fatura"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    fatura_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fatura.id", ondelete="CASCADE"), nullable=False
    )
    serial_medidor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    posto_horario: Mapped[PostoHorario] = mapped_column(
        SAEnum(PostoHorario, name="posto_horario_enum", create_constraint=False),
        nullable=False,
        default=PostoHorario.UNICO,
    )
    leitura_anterior: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    leitura_atual: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    constante_medidor: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("1")
    )
    consumo_kwh: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)

    fatura: Mapped["Fatura"] = relationship(back_populates="medidas", lazy="raise")

    __table_args__ = (Index("ix_medida_fatura", "fatura_id"),)


class ItemFatura(Base):
    __tablename__ = "item_fatura"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    fatura_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fatura.id", ondelete="CASCADE"), nullable=False
    )
    tipo_item: Mapped[TipoItem] = mapped_column(
        SAEnum(TipoItem, name="tipo_item_enum", create_constraint=True), nullable=False
    )
    descricao: Mapped[str] = mapped_column(String(500), nullable=False)
    quantidade: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    tarifa_unitaria: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    base_icms: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    aliquota_icms: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    ordem: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    fatura: Mapped["Fatura"] = relationship(back_populates="itens", lazy="raise")

    __table_args__ = (
        Index("ix_item_fatura", "fatura_id"),
        Index("ix_item_tipo", "tipo_item"),
    )


class TributoFatura(Base):
    __tablename__ = "tributo_fatura"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    fatura_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fatura.id", ondelete="CASCADE"), nullable=False
    )
    tipo_tributo: Mapped[TipoTributo] = mapped_column(
        SAEnum(TipoTributo, name="tipo_tributo_enum", create_constraint=True), nullable=False
    )
    base_calculo: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    aliquota: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    fatura: Mapped["Fatura"] = relationship(back_populates="tributos", lazy="raise")

    __table_args__ = (
        UniqueConstraint("fatura_id", "tipo_tributo", name="uq_tributo_fatura_tipo"),
        Index("ix_tributo_fatura", "fatura_id"),
    )
