import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.app.core.enums import (
    ModoDevolucao,
    StatusAchado,
    StatusExecucao,
)
from src.app.core.enums import (
    ResultadoRegra as ResultadoRegraEnum,
)
from src.app.domains.regulatorio.enums import CategoriaRegra, Severidade


class ResultadoRegraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    execucao_validacao_id: uuid.UUID
    regra_validacao_id: uuid.UUID
    resultado: ResultadoRegraEnum
    valor_esperado: dict | None
    valor_encontrado: dict | None
    diferenca: dict | None
    severidade: Severidade
    mensagem: str
    avaliado_em: datetime


class AchadoCreate(BaseModel):
    fatura_id: uuid.UUID
    execucao_validacao_id: uuid.UUID | None = None
    item_fatura_id: uuid.UUID | None = None
    resultado_regra_id: uuid.UUID | None = None
    titulo: str = Field(min_length=1, max_length=500)
    descricao: str = Field(min_length=1)
    categoria: CategoriaRegra
    severidade: Severidade
    valor_cobrado_a_maior: Decimal = Field(default=Decimal("0"), ge=0)
    modo_devolucao_estimado: ModoDevolucao | None = None


class AchadoUpdate(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=500)
    descricao: str | None = Field(default=None, min_length=1)
    categoria: CategoriaRegra | None = None
    severidade: Severidade | None = None
    status: StatusAchado | None = None
    valor_cobrado_a_maior: Decimal | None = Field(default=None, ge=0)
    modo_devolucao_estimado: ModoDevolucao | None = None


class AchadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fatura_id: uuid.UUID
    execucao_validacao_id: uuid.UUID | None
    item_fatura_id: uuid.UUID | None
    resultado_regra_id: uuid.UUID | None
    revisor_id: uuid.UUID | None
    titulo: str
    descricao: str
    categoria: CategoriaRegra
    severidade: Severidade
    status: StatusAchado
    valor_cobrado_a_maior: Decimal
    modo_devolucao_estimado: ModoDevolucao | None
    revisado_em: datetime | None
    criado_em: datetime


class AchadosOut(BaseModel):
    itens: list[AchadoOut]
    total: int


class ExecucaoValidacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fatura_id: uuid.UUID
    pacote_regras_id: uuid.UUID
    snapshot_tarifa_id: uuid.UUID | None
    disparado_por_id: uuid.UUID
    status: StatusExecucao
    total_regras_avaliadas: int
    total_achados: int
    valor_total_cobrado_a_maior: Decimal
    iniciado_em: datetime
    finalizado_em: datetime | None
    erro: str | None


class ExecucaoValidacaoDetalheOut(ExecucaoValidacaoOut):
    resultados: list[ResultadoRegraOut]
    achados: list[AchadoOut]
