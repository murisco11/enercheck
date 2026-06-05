import re
import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.app.core.enums import (
    Bandeira,
    BaseLeitura,
    ModalidadeTarifaria,
    PostoHorario,
    TipoItem,
    TipoTributo,
)

CENTAVO = Decimal("0.01")
COMPETENCIA_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class MedidaFaturaCreate(BaseModel):
    serial_medidor: str | None = Field(default=None, max_length=100)
    posto_horario: PostoHorario = PostoHorario.UNICO
    leitura_anterior: Decimal = Field(ge=0)
    leitura_atual: Decimal = Field(ge=0)
    constante_medidor: Decimal = Field(default=Decimal("1"), gt=0)
    consumo_kwh: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def validar_leituras(self) -> "MedidaFaturaCreate":
        if self.leitura_atual < self.leitura_anterior:
            raise ValueError("leitura_atual deve ser maior ou igual a leitura_anterior")
        return self


class MedidaFaturaUpdate(BaseModel):
    serial_medidor: str | None = Field(default=None, max_length=100)
    posto_horario: PostoHorario | None = None
    leitura_anterior: Decimal | None = Field(default=None, ge=0)
    leitura_atual: Decimal | None = Field(default=None, ge=0)
    constante_medidor: Decimal | None = Field(default=None, gt=0)
    consumo_kwh: Decimal | None = Field(default=None, ge=0)


class MedidaFaturaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fatura_id: uuid.UUID
    serial_medidor: str | None
    posto_horario: PostoHorario
    leitura_anterior: Decimal
    leitura_atual: Decimal
    constante_medidor: Decimal
    consumo_kwh: Decimal


class ItemFaturaCreate(BaseModel):
    tipo_item: TipoItem
    descricao: str = Field(min_length=1, max_length=500)
    quantidade: Decimal = Field(ge=0)
    tarifa_unitaria: Decimal = Field(ge=0)
    valor: Decimal
    base_icms: Decimal | None = Field(default=None, ge=0)
    aliquota_icms: Decimal | None = Field(default=None, ge=0)
    ordem: int | None = Field(default=None, ge=0, le=32767)


class ItemFaturaUpdate(BaseModel):
    tipo_item: TipoItem | None = None
    descricao: str | None = Field(default=None, min_length=1, max_length=500)
    quantidade: Decimal | None = Field(default=None, ge=0)
    tarifa_unitaria: Decimal | None = Field(default=None, ge=0)
    valor: Decimal | None = None
    base_icms: Decimal | None = Field(default=None, ge=0)
    aliquota_icms: Decimal | None = Field(default=None, ge=0)
    ordem: int | None = Field(default=None, ge=0, le=32767)


class ItemFaturaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fatura_id: uuid.UUID
    tipo_item: TipoItem
    descricao: str
    quantidade: Decimal
    tarifa_unitaria: Decimal
    valor: Decimal
    base_icms: Decimal | None
    aliquota_icms: Decimal | None
    ordem: int | None


class TributoFaturaCreate(BaseModel):
    tipo_tributo: TipoTributo
    base_calculo: Decimal = Field(ge=0)
    aliquota: Decimal = Field(ge=0)
    valor: Decimal = Field(ge=0)


class TributoFaturaUpdate(BaseModel):
    tipo_tributo: TipoTributo | None = None
    base_calculo: Decimal | None = Field(default=None, ge=0)
    aliquota: Decimal | None = Field(default=None, ge=0)
    valor: Decimal | None = Field(default=None, ge=0)


class TributoFaturaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fatura_id: uuid.UUID
    tipo_tributo: TipoTributo
    base_calculo: Decimal
    aliquota: Decimal
    valor: Decimal


class FaturaCreate(BaseModel):
    unidade_consumidora_id: uuid.UUID
    documento_bruto_id: uuid.UUID | None = None
    lote_auditoria_id: uuid.UUID | None = None
    numero_nota: str | None = Field(default=None, max_length=100)
    chave_acesso: str | None = Field(default=None, max_length=100)
    competencia: str
    data_emissao: date | None = None
    data_vencimento: date | None = None
    data_leitura_anterior: date | None = None
    data_leitura_atual: date | None = None
    dias_faturados: int | None = Field(default=None, ge=0, le=366)
    bandeira: Bandeira | None = None
    valor_total: Decimal = Field(ge=0)
    modalidade: ModalidadeTarifaria
    base_leitura: BaseLeitura = BaseLeitura.REAL
    medidas: list[MedidaFaturaCreate] = Field(default_factory=list)
    itens: list[ItemFaturaCreate] = Field(default_factory=list)
    tributos: list[TributoFaturaCreate] = Field(default_factory=list)

    @field_validator("competencia")
    @classmethod
    def validar_competencia(cls, v: str) -> str:
        if not COMPETENCIA_RE.fullmatch(v):
            raise ValueError("competencia deve estar no formato YYYY-MM")
        return v

    @model_validator(mode="after")
    def validar_datas(self) -> "FaturaCreate":
        if (
            self.data_leitura_anterior is not None
            and self.data_leitura_atual is not None
            and self.data_leitura_atual < self.data_leitura_anterior
        ):
            raise ValueError("data_leitura_atual deve ser posterior à data_leitura_anterior")
        return self


class FaturaUpdate(BaseModel):
    documento_bruto_id: uuid.UUID | None = None
    lote_auditoria_id: uuid.UUID | None = None
    numero_nota: str | None = Field(default=None, max_length=100)
    chave_acesso: str | None = Field(default=None, max_length=100)
    competencia: str | None = None
    data_emissao: date | None = None
    data_vencimento: date | None = None
    data_leitura_anterior: date | None = None
    data_leitura_atual: date | None = None
    dias_faturados: int | None = Field(default=None, ge=0, le=366)
    bandeira: Bandeira | None = None
    valor_total: Decimal | None = Field(default=None, ge=0)
    modalidade: ModalidadeTarifaria | None = None
    base_leitura: BaseLeitura | None = None

    @field_validator("competencia")
    @classmethod
    def validar_competencia(cls, v: str | None) -> str | None:
        if v is not None and not COMPETENCIA_RE.fullmatch(v):
            raise ValueError("competencia deve estar no formato YYYY-MM")
        return v


class FaturaResumoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    unidade_consumidora_id: uuid.UUID
    documento_bruto_id: uuid.UUID | None
    lote_auditoria_id: uuid.UUID | None
    numero_nota: str | None
    chave_acesso: str | None
    competencia: str
    valor_total: Decimal
    modalidade: ModalidadeTarifaria
    base_leitura: BaseLeitura
    criada_em: datetime


class FaturasOut(BaseModel):
    itens: list[FaturaResumoOut]
    total: int


class FaturaOut(FaturaResumoOut):
    data_emissao: date | None
    data_vencimento: date | None
    data_leitura_anterior: date | None
    data_leitura_atual: date | None
    dias_faturados: int | None
    bandeira: Bandeira | None


class FaturaDetalheOut(FaturaOut):
    medidas: list[MedidaFaturaOut]
    itens: list[ItemFaturaOut]
    tributos: list[TributoFaturaOut]
