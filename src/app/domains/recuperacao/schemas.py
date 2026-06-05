import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.app.core.enums import (
    CanalRecuperacao,
    ModoDevolucao,
    Prioridade,
    StatusItem,
    StatusRecuperacao,
)


class CasoRecuperacaoCreate(BaseModel):
    cliente_id: uuid.UUID
    unidade_consumidora_id: uuid.UUID
    lote_auditoria_id: uuid.UUID | None = None
    responsavel_id: uuid.UUID | None = None
    numero_caso: str | None = Field(default=None, max_length=100)
    status: StatusRecuperacao = StatusRecuperacao.ABERTO
    prioridade: Prioridade = Prioridade.MEDIA
    canal_protocolo: CanalRecuperacao | None = None
    numero_protocolo: str | None = Field(default=None, max_length=100)
    protocolado_em: datetime | None = None


class CasoRecuperacaoUpdate(BaseModel):
    responsavel_id: uuid.UUID | None = None
    numero_caso: str | None = Field(default=None, max_length=100)
    status: StatusRecuperacao | None = None
    prioridade: Prioridade | None = None
    canal_protocolo: CanalRecuperacao | None = None
    numero_protocolo: str | None = Field(default=None, max_length=100)
    protocolado_em: datetime | None = None
    fechado_em: datetime | None = None


class ItemRecuperacaoCreate(BaseModel):
    achado_id: uuid.UUID
    fatura_id: uuid.UUID
    valor_cobrado_a_maior: Decimal = Field(ge=0)
    modo_devolucao: ModoDevolucao | None = None
    valor_recuperavel: Decimal | None = Field(default=None, ge=0)
    valor_reconhecido: Decimal = Field(default=Decimal("0"), ge=0)
    valor_devolvido: Decimal = Field(default=Decimal("0"), ge=0)
    status: StatusItem = StatusItem.ABERTO


class ItemRecuperacaoUpdate(BaseModel):
    modo_devolucao: ModoDevolucao | None = None
    valor_recuperavel: Decimal | None = Field(default=None, ge=0)
    valor_reconhecido: Decimal | None = Field(default=None, ge=0)
    valor_devolvido: Decimal | None = Field(default=None, ge=0)
    status: StatusItem | None = None


class ItemRecuperacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    caso_recuperacao_id: uuid.UUID
    achado_id: uuid.UUID
    fatura_id: uuid.UUID
    valor_cobrado_a_maior: Decimal
    modo_devolucao: ModoDevolucao | None
    valor_recuperavel: Decimal
    valor_reconhecido: Decimal
    valor_devolvido: Decimal
    status: StatusItem


class CasoRecuperacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cliente_id: uuid.UUID
    unidade_consumidora_id: uuid.UUID
    lote_auditoria_id: uuid.UUID | None
    responsavel_id: uuid.UUID | None
    criado_por_id: uuid.UUID
    numero_caso: str
    status: StatusRecuperacao
    prioridade: Prioridade
    total_estimado: Decimal
    total_recuperavel: Decimal
    total_reconhecido: Decimal
    total_devolvido: Decimal
    canal_protocolo: CanalRecuperacao | None
    numero_protocolo: str | None
    protocolado_em: datetime | None
    aberto_em: datetime
    fechado_em: datetime | None


class CasoRecuperacaoDetalheOut(CasoRecuperacaoOut):
    itens: list[ItemRecuperacaoOut]


class CasosRecuperacaoOut(BaseModel):
    itens: list[CasoRecuperacaoOut]
    total: int
