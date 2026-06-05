import re
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.app.core.enums import StatusExtracao


class LayoutFaturaCreate(BaseModel):
    distribuidora_id: uuid.UUID
    codigo: str = Field(min_length=1, max_length=100)
    descricao: str = Field(min_length=1, max_length=500)
    extrator_classe: str = Field(min_length=1, max_length=255)
    vigencia_inicio: date
    vigencia_fim: date | None = None
    assinatura_deteccao: dict | None = None
    ativo: bool = True

    @model_validator(mode="after")
    def validar_vigencia(self) -> "LayoutFaturaCreate":
        if self.vigencia_fim is not None and self.vigencia_fim < self.vigencia_inicio:
            raise ValueError("vigencia_fim deve ser igual ou posterior a vigencia_inicio")
        return self


class LayoutFaturaUpdate(BaseModel):
    distribuidora_id: uuid.UUID | None = None
    codigo: str | None = Field(default=None, min_length=1, max_length=100)
    descricao: str | None = Field(default=None, min_length=1, max_length=500)
    extrator_classe: str | None = Field(default=None, min_length=1, max_length=255)
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None
    assinatura_deteccao: dict | None = None
    ativo: bool | None = None


class LayoutFaturaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    distribuidora_id: uuid.UUID
    codigo: str
    descricao: str
    extrator_classe: str
    vigencia_inicio: date
    vigencia_fim: date | None
    assinatura_deteccao: dict | None
    ativo: bool


class DocumentoBrutoCreate(BaseModel):
    unidade_consumidora_id: uuid.UUID
    lote_auditoria_id: uuid.UUID | None = None
    layout_fatura_id: uuid.UUID | None = None
    uri_armazenamento: str = Field(min_length=1, max_length=1000)
    nome_original: str = Field(min_length=1, max_length=255)
    sha256: str = Field(min_length=64, max_length=64)
    payload_extracao: dict | None = None

    @field_validator("sha256")
    @classmethod
    def validar_sha256(cls, v: str) -> str:
        value = v.lower()
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("sha256 deve ser hexadecimal com 64 caracteres")
        return value


class DocumentoBrutoUpdate(BaseModel):
    lote_auditoria_id: uuid.UUID | None = None
    layout_fatura_id: uuid.UUID | None = None
    uri_armazenamento: str | None = Field(default=None, min_length=1, max_length=1000)
    nome_original: str | None = Field(default=None, min_length=1, max_length=255)


class DocumentoBrutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    unidade_consumidora_id: uuid.UUID
    lote_auditoria_id: uuid.UUID | None
    enviado_por_id: uuid.UUID
    layout_fatura_id: uuid.UUID | None
    uri_armazenamento: str
    nome_original: str
    sha256: str
    status_extracao: StatusExtracao
    payload_extracao: dict | None
    erro_extracao: str | None
    enviado_em: datetime


class DocumentoBrutoResumoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    unidade_consumidora_id: uuid.UUID
    lote_auditoria_id: uuid.UUID | None
    nome_original: str
    sha256: str
    status_extracao: StatusExtracao
    enviado_em: datetime


class DocumentosBrutosOut(BaseModel):
    itens: list[DocumentoBrutoResumoOut]
    total: int
