import re
import uuid
from datetime import date, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.app.core.enums import Grupo, ModalidadeTarifaria, StatusLote, Subgrupo

T = TypeVar("T")

_SUBGRUPOS_A = {Subgrupo.A1, Subgrupo.A2, Subgrupo.A3, Subgrupo.A3a, Subgrupo.A4, Subgrupo.AS}
_SUBGRUPOS_B = {Subgrupo.B1, Subgrupo.B2, Subgrupo.B3, Subgrupo.B4}


def _limpar_cnpj(v: str) -> str:
    digits = re.sub(r"\D", "", v)
    if len(digits) != 14:
        raise ValueError("CNPJ deve ter 14 dígitos")
    return digits


# ===== Distribuidora =====


class DistribuidoraCreate(BaseModel):
    razao_social: str = Field(min_length=1, max_length=255)
    cnpj: str
    sigla: str = Field(min_length=1, max_length=20)
    estado: str = Field(min_length=2, max_length=2)

    @field_validator("cnpj")
    @classmethod
    def validar_cnpj(cls, v: str) -> str:
        return _limpar_cnpj(v)

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v: str) -> str:
        return v.upper()


class DistribuidoraUpdate(BaseModel):
    razao_social: str | None = Field(default=None, min_length=1, max_length=255)
    cnpj: str | None = None
    sigla: str | None = Field(default=None, min_length=1, max_length=20)
    estado: str | None = Field(default=None, min_length=2, max_length=2)
    ativo: bool | None = None

    @field_validator("cnpj")
    @classmethod
    def validar_cnpj(cls, v: str | None) -> str | None:
        return _limpar_cnpj(v) if v else v

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v: str | None) -> str | None:
        return v.upper() if v else v


class DistribuidoraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    razao_social: str
    cnpj: str
    sigla: str
    estado: str
    ativo: bool


# ===== Cliente =====


class ClienteCreate(BaseModel):
    razao_social: str = Field(min_length=1, max_length=255)
    nome_fantasia: str | None = Field(default=None, max_length=255)
    cnpj: str

    @field_validator("cnpj")
    @classmethod
    def validar_cnpj(cls, v: str) -> str:
        return _limpar_cnpj(v)


class ClienteUpdate(BaseModel):
    razao_social: str | None = Field(default=None, min_length=1, max_length=255)
    nome_fantasia: str | None = Field(default=None, max_length=255)


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    razao_social: str
    nome_fantasia: str | None
    cnpj: str
    ativo: bool
    criado_em: datetime


class ClienteResumoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    razao_social: str
    nome_fantasia: str | None
    cnpj: str
    ativo: bool


class ClientesOut(BaseModel):
    itens: list[ClienteResumoOut]
    total: int


# ===== AcessoCliente =====


class AcessoClienteCreate(BaseModel):
    usuario_id: uuid.UUID
    pode_editar: bool = False


class AcessoClienteUpdate(BaseModel):
    pode_editar: bool | None = None


class AcessoClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    usuario_id: uuid.UUID
    cliente_id: uuid.UUID
    pode_editar: bool


class AcessosClienteOut(BaseModel):
    itens: list[AcessoClienteOut]
    total: int


# ===== UnidadeConsumidora =====


class UnidadeConsumidoraCreate(BaseModel):
    distribuidora_id: uuid.UUID
    codigo_instalacao: str = Field(min_length=1, max_length=50)
    codigo_cliente: str | None = Field(default=None, max_length=50)
    grupo: Grupo
    subgrupo: Subgrupo
    modalidade: ModalidadeTarifaria
    tarifa_social: bool = False
    cidade: str = Field(min_length=1, max_length=100)
    estado: str = Field(min_length=2, max_length=2)

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def validar_grupo_subgrupo(self) -> "UnidadeConsumidoraCreate":
        if self.grupo == Grupo.A and self.subgrupo not in _SUBGRUPOS_A:
            raise ValueError(f"Subgrupo {self.subgrupo} incompatível com Grupo A")
        if self.grupo == Grupo.B and self.subgrupo not in _SUBGRUPOS_B:
            raise ValueError(f"Subgrupo {self.subgrupo} incompatível com Grupo B")
        return self


class UnidadeConsumidoraUpdate(BaseModel):
    codigo_instalacao: str | None = Field(default=None, min_length=1, max_length=50)
    codigo_cliente: str | None = None
    grupo: Grupo | None = None
    subgrupo: Subgrupo | None = None
    modalidade: ModalidadeTarifaria | None = None
    tarifa_social: bool | None = None
    cidade: str | None = Field(default=None, min_length=1, max_length=100)
    estado: str | None = Field(default=None, min_length=2, max_length=2)

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v: str | None) -> str | None:
        return v.upper() if v else v

    @model_validator(mode="after")
    def validar_grupo_subgrupo(self) -> "UnidadeConsumidoraUpdate":
        if self.grupo is not None and self.subgrupo is not None:
            if self.grupo == Grupo.A and self.subgrupo not in _SUBGRUPOS_A:
                raise ValueError(f"Subgrupo {self.subgrupo} incompatível com Grupo A")
            if self.grupo == Grupo.B and self.subgrupo not in _SUBGRUPOS_B:
                raise ValueError(f"Subgrupo {self.subgrupo} incompatível com Grupo B")
        return self


class UnidadeConsumidoraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cliente_id: uuid.UUID
    distribuidora_id: uuid.UUID
    codigo_instalacao: str
    codigo_cliente: str | None
    grupo: Grupo
    subgrupo: Subgrupo
    modalidade: ModalidadeTarifaria
    tarifa_social: bool
    cidade: str
    estado: str
    criado_em: datetime


class UnidadeConsumidoraResumoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cliente_id: uuid.UUID
    distribuidora_id: uuid.UUID
    codigo_instalacao: str
    grupo: Grupo
    subgrupo: Subgrupo
    modalidade: ModalidadeTarifaria
    cidade: str
    estado: str


class UCsOut(BaseModel):
    itens: list[UnidadeConsumidoraResumoOut]
    total: int


# ===== LoteAuditoria =====


class LoteCreate(BaseModel):
    unidade_consumidora_id: uuid.UUID
    rotulo: str = Field(min_length=1, max_length=255)
    competencia_inicio: date
    competencia_fim: date

    @model_validator(mode="after")
    def validar_competencias(self) -> "LoteCreate":
        if self.competencia_fim < self.competencia_inicio:
            raise ValueError("competencia_fim deve ser igual ou posterior a competencia_inicio")
        return self


class LoteUpdate(BaseModel):
    rotulo: str | None = Field(default=None, min_length=1, max_length=255)
    status: StatusLote | None = None


class LoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    unidade_consumidora_id: uuid.UUID
    criado_por_id: uuid.UUID
    rotulo: str
    status: StatusLote
    competencia_inicio: date
    competencia_fim: date
    criado_em: datetime


class LoteResumoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    unidade_consumidora_id: uuid.UUID
    rotulo: str
    status: StatusLote
    competencia_inicio: date
    competencia_fim: date


# ===== Paginação keyset =====


class PaginacaoKeyset(BaseModel):
    after_id: uuid.UUID | None = None
    limite: int = Field(default=50, ge=1, le=200)


class PageKeysetOut(BaseModel, Generic[T]):
    data: list[T]
    next_cursor: uuid.UUID | None
    has_more: bool
