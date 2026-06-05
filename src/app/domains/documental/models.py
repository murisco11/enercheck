import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.app.core.enums import StatusExtracao
from src.app.db.mixins import SoftDeleteMixin
from src.app.db.session import Base

JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class LayoutFatura(SoftDeleteMixin, Base):
    __tablename__ = "layout_fatura"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    distribuidora_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("distribuidora.id"), nullable=False
    )
    codigo: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    descricao: Mapped[str] = mapped_column(String(500), nullable=False)
    extrator_classe: Mapped[str] = mapped_column(String(255), nullable=False)
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    assinatura_deteccao: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    ativo: Mapped[bool] = mapped_column(nullable=False, default=True)

    __table_args__ = (
        Index("ix_layout_distribuidora", "distribuidora_id"),
        Index("ix_layout_codigo", "codigo"),
    )


class DocumentoBruto(Base):
    __tablename__ = "documento_bruto"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    unidade_consumidora_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("unidade_consumidora.id"), nullable=False
    )
    lote_auditoria_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lote_auditoria.id"), nullable=True
    )
    enviado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    layout_fatura_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("layout_fatura.id"), nullable=True
    )
    uri_armazenamento: Mapped[str] = mapped_column(String(1000), nullable=False)
    nome_original: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status_extracao: Mapped[StatusExtracao] = mapped_column(
        SAEnum(StatusExtracao, name="status_extracao_enum", create_constraint=True),
        nullable=False,
        default=StatusExtracao.PENDENTE,
    )
    payload_extracao: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    erro_extracao: Mapped[str | None] = mapped_column(Text, nullable=True)
    enviado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_documento_uc", "unidade_consumidora_id"),
        Index("ix_documento_lote", "lote_auditoria_id"),
        Index("ix_documento_sha256", "sha256"),
        Index("ix_documento_status", "status_extracao"),
    )
