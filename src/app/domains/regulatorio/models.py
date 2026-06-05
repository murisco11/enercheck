import uuid
from datetime import date
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.core.enums import Bandeira, Grupo, ModalidadeTarifaria, PostoHorario, Subgrupo
from src.app.db.mixins import SoftDeleteMixin, TimestampMixin
from src.app.db.session import Base
from src.app.domains.regulatorio.enums import (
    CategoriaRegra,
    OrigemRegulatoria,
    Severidade,
    StatusDocumento,
    TipoDocumento,
)

EMBEDDING_DIM = 1536  # text-embedding-3-small
JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")
EMBEDDING_TYPE = Vector(EMBEDDING_DIM).with_variant(JSON(), "sqlite")


class DocumentoRegulatorio(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "documento_regulatorio"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    identificador: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    titulo: Mapped[str] = mapped_column(String(500), nullable=False)
    origem: Mapped[OrigemRegulatoria] = mapped_column(
        SAEnum(OrigemRegulatoria, name="origem_regulatoria_enum", create_constraint=True),
        nullable=False,
    )
    tipo: Mapped[TipoDocumento] = mapped_column(
        SAEnum(TipoDocumento, name="tipo_documento_enum", create_constraint=True),
        nullable=False,
    )
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    uri_armazenamento: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[StatusDocumento] = mapped_column(
        SAEnum(StatusDocumento, name="status_documento_enum", create_constraint=True),
        nullable=False,
        default=StatusDocumento.ATIVO,
    )

    chunks: Mapped[list["ChunkRegulatorio"]] = relationship(
        back_populates="documento",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    snapshots_tarifa: Mapped[list["SnapshotTarifa"]] = relationship(
        back_populates="documento_origem",
        lazy="raise",
    )
    regras: Mapped[list["RegraValidacao"]] = relationship(
        back_populates="documento_origem",
        lazy="raise",
    )

    __table_args__ = (
        Index("ix_doc_reg_identificador", "identificador"),
        Index("ix_doc_reg_status", "status"),
    )


class ChunkRegulatorio(Base):
    __tablename__ = "chunk_regulatorio"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    documento_regulatorio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documento_regulatorio.id", ondelete="CASCADE"), nullable=False
    )
    indice: Mapped[int] = mapped_column(Integer, nullable=False)
    caminho_secao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    hash_conteudo: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(EMBEDDING_TYPE, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    documento: Mapped["DocumentoRegulatorio"] = relationship(
        back_populates="chunks", lazy="raise"
    )

    __table_args__ = (
        UniqueConstraint(
            "documento_regulatorio_id", "indice", name="uq_chunk_documento_indice"
        ),
        Index("ix_chunk_documento", "documento_regulatorio_id"),
        # Índice HNSW criado no lifespan da app (ver main.py) — pgvector não
        # suporta criação via DDL automático do SQLAlchemy.
    )


class SnapshotTarifa(SoftDeleteMixin, Base):
    __tablename__ = "snapshot_tarifa"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    distribuidora_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("distribuidora.id"), nullable=False
    )
    documento_origem_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documento_regulatorio.id"), nullable=True
    )
    grupo: Mapped[Grupo] = mapped_column(
        SAEnum(Grupo, name="grupo_enum", create_constraint=False), nullable=False
    )
    subgrupo: Mapped[Subgrupo] = mapped_column(
        SAEnum(Subgrupo, name="subgrupo_enum", create_constraint=False), nullable=False
    )
    modalidade: Mapped[ModalidadeTarifaria] = mapped_column(
        SAEnum(ModalidadeTarifaria, name="modalidade_tarifaria_enum", create_constraint=False),
        nullable=False,
    )
    posto_horario: Mapped[PostoHorario | None] = mapped_column(
        SAEnum(PostoHorario, name="posto_horario_enum", create_constraint=True),
        nullable=True,
    )
    bandeira: Mapped[Bandeira | None] = mapped_column(
        SAEnum(Bandeira, name="bandeira_enum", create_constraint=False), nullable=True
    )
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    valor_tusd: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    valor_te: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    valor_tusd_com_tributos: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    valor_te_com_tributos: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    adicional_bandeira: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0")
    )
    resolucao_origem: Mapped[str | None] = mapped_column(String(100), nullable=True)

    documento_origem: Mapped["DocumentoRegulatorio | None"] = relationship(
        back_populates="snapshots_tarifa", lazy="raise"
    )

    __table_args__ = (
        Index("ix_snapshot_distribuidora", "distribuidora_id"),
        Index("ix_snapshot_vigencia", "vigencia_inicio", "vigencia_fim"),
    )


class PacoteRegras(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "pacote_regras"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    versao: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    vigente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    publicado_por_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuario.id"), nullable=True
    )

    regras: Mapped[list["RegraValidacao"]] = relationship(
        back_populates="pacote",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    __table_args__ = (Index("ix_pacote_regras_vigente", "vigente"),)


class RegraValidacao(Base):
    __tablename__ = "regra_validacao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pacote_regras_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pacote_regras.id", ondelete="CASCADE"), nullable=False
    )
    documento_origem_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documento_regulatorio.id"), nullable=True
    )
    codigo: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    categoria: Mapped[CategoriaRegra] = mapped_column(
        SAEnum(CategoriaRegra, name="categoria_regra_enum", create_constraint=True),
        nullable=False,
    )
    severidade: Mapped[Severidade] = mapped_column(
        SAEnum(Severidade, name="severidade_enum", create_constraint=True),
        nullable=False,
    )
    aplica_grupo: Mapped[Grupo | None] = mapped_column(
        SAEnum(Grupo, name="grupo_enum", create_constraint=False), nullable=True
    )
    aplica_subgrupo: Mapped[Subgrupo | None] = mapped_column(
        SAEnum(Subgrupo, name="subgrupo_enum", create_constraint=False), nullable=True
    )
    aplica_modalidade: Mapped[ModalidadeTarifaria | None] = mapped_column(
        SAEnum(ModalidadeTarifaria, name="modalidade_tarifaria_enum", create_constraint=False),
        nullable=True,
    )
    vigencia_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    vigencia_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    expressao_logica: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    pacote: Mapped["PacoteRegras"] = relationship(back_populates="regras", lazy="raise")
    documento_origem: Mapped["DocumentoRegulatorio | None"] = relationship(
        back_populates="regras", lazy="raise"
    )

    __table_args__ = (
        Index("ix_regra_pacote", "pacote_regras_id"),
        Index("ix_regra_codigo", "codigo"),
        Index("ix_regra_ativa", "ativa"),
    )
