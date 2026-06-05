import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Numeric, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.core.enums import ModoDevolucao, StatusAchado, StatusExecucao
from src.app.core.enums import ResultadoRegra as ResultadoRegraEnum
from src.app.db.session import Base
from src.app.domains.regulatorio.enums import CategoriaRegra, Severidade

JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class ExecucaoValidacao(Base):
    __tablename__ = "execucao_validacao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    fatura_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fatura.id"), nullable=False)
    pacote_regras_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pacote_regras.id"), nullable=False
    )
    snapshot_tarifa_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("snapshot_tarifa.id"), nullable=True
    )
    disparado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    status: Mapped[StatusExecucao] = mapped_column(
        SAEnum(StatusExecucao, name="status_execucao_enum", create_constraint=True),
        nullable=False,
        default=StatusExecucao.PENDENTE,
    )
    total_regras_avaliadas: Mapped[int] = mapped_column(nullable=False, default=0)
    total_achados: Mapped[int] = mapped_column(nullable=False, default=0)
    valor_total_cobrado_a_maior: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    iniciado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finalizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)

    resultados: Mapped[list["ResultadoRegra"]] = relationship(
        back_populates="execucao", cascade="all, delete-orphan", lazy="raise"
    )
    achados: Mapped[list["Achado"]] = relationship(
        back_populates="execucao", cascade="all, delete-orphan", lazy="raise"
    )

    __table_args__ = (
        Index("ix_execucao_fatura", "fatura_id"),
        Index("ix_execucao_pacote", "pacote_regras_id"),
    )


class ResultadoRegra(Base):
    __tablename__ = "resultado_regra"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    execucao_validacao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("execucao_validacao.id", ondelete="CASCADE"), nullable=False
    )
    regra_validacao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("regra_validacao.id"), nullable=False
    )
    resultado: Mapped[ResultadoRegraEnum] = mapped_column(
        SAEnum(ResultadoRegraEnum, name="resultado_regra_enum", create_constraint=True),
        nullable=False,
    )
    valor_esperado: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    valor_encontrado: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    diferenca: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    severidade: Mapped[Severidade] = mapped_column(
        SAEnum(Severidade, name="severidade_enum", create_constraint=False),
        nullable=False,
    )
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    avaliado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    execucao: Mapped["ExecucaoValidacao"] = relationship(back_populates="resultados", lazy="raise")
    achados: Mapped[list["Achado"]] = relationship(back_populates="resultado_regra", lazy="raise")

    __table_args__ = (
        Index("ix_resultado_execucao", "execucao_validacao_id"),
        Index("ix_resultado_regra", "regra_validacao_id"),
    )


class Achado(Base):
    __tablename__ = "achado"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    fatura_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fatura.id"), nullable=False)
    execucao_validacao_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("execucao_validacao.id"), nullable=True
    )
    item_fatura_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("item_fatura.id"), nullable=True
    )
    resultado_regra_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resultado_regra.id"), nullable=True
    )
    revisor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    categoria: Mapped[CategoriaRegra] = mapped_column(
        SAEnum(CategoriaRegra, name="categoria_regra_enum", create_constraint=False),
        nullable=False,
    )
    severidade: Mapped[Severidade] = mapped_column(
        SAEnum(Severidade, name="severidade_enum", create_constraint=False),
        nullable=False,
    )
    status: Mapped[StatusAchado] = mapped_column(
        SAEnum(StatusAchado, name="status_achado_enum", create_constraint=True),
        nullable=False,
        default=StatusAchado.ABERTO,
    )
    valor_cobrado_a_maior: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    modo_devolucao_estimado: Mapped[ModoDevolucao | None] = mapped_column(
        SAEnum(ModoDevolucao, name="modo_devolucao_enum", create_constraint=True),
        nullable=True,
    )
    revisado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    execucao: Mapped["ExecucaoValidacao | None"] = relationship(
        back_populates="achados", lazy="raise"
    )
    resultado_regra: Mapped["ResultadoRegra | None"] = relationship(
        back_populates="achados", lazy="raise"
    )

    __table_args__ = (
        Index("ix_achado_fatura", "fatura_id"),
        Index("ix_achado_execucao", "execucao_validacao_id"),
        Index("ix_achado_status", "status"),
    )
