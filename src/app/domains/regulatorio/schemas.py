import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.app.core.enums import Bandeira, Grupo, ModalidadeTarifaria, PostoHorario, Subgrupo
from src.app.domains.regulatorio.enums import (
    CategoriaRegra,
    OrigemRegulatoria,
    Severidade,
    StatusDocumento,
    TipoDocumento,
)


class DocumentoRegulatorioCreate(BaseModel):
    identificador: str = Field(max_length=100)
    titulo: str = Field(max_length=500)
    origem: OrigemRegulatoria
    tipo: TipoDocumento
    vigencia_inicio: date
    vigencia_fim: date | None = None
    uri_armazenamento: str | None = None
    status: StatusDocumento = StatusDocumento.ATIVO

    @model_validator(mode="after")
    def validar_vigencia(self) -> "DocumentoRegulatorioCreate":
        if self.vigencia_fim is not None and self.vigencia_fim < self.vigencia_inicio:
            raise ValueError("vigencia_fim deve ser igual ou posterior a vigencia_inicio")
        return self


class DocumentoRegulatorioUpdate(BaseModel):
    identificador: str | None = Field(default=None, max_length=100)
    titulo: str | None = Field(default=None, max_length=500)
    origem: OrigemRegulatoria | None = None
    tipo: TipoDocumento | None = None
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None
    uri_armazenamento: str | None = None
    status: StatusDocumento | None = None
    ativo: bool | None = None


class DocumentoRegulatorioOut(DocumentoRegulatorioCreate):
    id: uuid.UUID
    criado_em: datetime
    atualizado_em: datetime
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


class ChunkCreate(BaseModel):
    indice: int
    caminho_secao: str | None = None
    conteudo: str
    hash_conteudo: str = Field(max_length=64)
    total_tokens: int | None = None


class ChunkOut(ChunkCreate):
    id: uuid.UUID
    documento_regulatorio_id: uuid.UUID
    # embedding omitido — vetores não são serializados em respostas da API

    model_config = {"from_attributes": True}


class SnapshotTarifaCreate(BaseModel):
    distribuidora_id: uuid.UUID
    documento_origem_id: uuid.UUID | None = None
    grupo: Grupo
    subgrupo: Subgrupo
    modalidade: ModalidadeTarifaria
    posto_horario: PostoHorario | None = None
    bandeira: Bandeira | None = None
    vigencia_inicio: date
    vigencia_fim: date | None = None
    valor_tusd: Decimal = Field(ge=0)
    valor_te: Decimal = Field(ge=0)
    valor_tusd_com_tributos: Decimal = Field(ge=0)
    valor_te_com_tributos: Decimal = Field(ge=0)
    adicional_bandeira: Decimal = Field(default=Decimal("0"), ge=0)
    resolucao_origem: str | None = None

    @model_validator(mode="after")
    def validar_vigencia(self) -> "SnapshotTarifaCreate":
        if self.vigencia_fim is not None and self.vigencia_fim < self.vigencia_inicio:
            raise ValueError("vigencia_fim deve ser igual ou posterior a vigencia_inicio")
        return self


class SnapshotTarifaUpdate(BaseModel):
    documento_origem_id: uuid.UUID | None = None
    grupo: Grupo | None = None
    subgrupo: Subgrupo | None = None
    modalidade: ModalidadeTarifaria | None = None
    posto_horario: PostoHorario | None = None
    bandeira: Bandeira | None = None
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None
    valor_tusd: Decimal | None = Field(default=None, ge=0)
    valor_te: Decimal | None = Field(default=None, ge=0)
    valor_tusd_com_tributos: Decimal | None = Field(default=None, ge=0)
    valor_te_com_tributos: Decimal | None = Field(default=None, ge=0)
    adicional_bandeira: Decimal | None = Field(default=None, ge=0)
    resolucao_origem: str | None = None
    ativo: bool | None = None


class SnapshotTarifaOut(SnapshotTarifaCreate):
    id: uuid.UUID
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


class PacoteRegrasCreate(BaseModel):
    versao: str = Field(max_length=50)
    descricao: str | None = None
    vigente: bool = False


class PacoteRegrasOut(PacoteRegrasCreate):
    id: uuid.UUID
    publicado_por_id: uuid.UUID | None
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class PacoteRegrasUpdate(BaseModel):
    versao: str | None = Field(default=None, max_length=50)
    descricao: str | None = None
    vigente: bool | None = None
    ativo: bool | None = None


class RegraValidacaoCreate(BaseModel):
    pacote_regras_id: uuid.UUID
    documento_origem_id: uuid.UUID | None = None
    codigo: str = Field(max_length=50)
    nome: str = Field(max_length=255)
    descricao: str | None = None
    categoria: CategoriaRegra
    severidade: Severidade
    aplica_grupo: Grupo | None = None
    aplica_subgrupo: Subgrupo | None = None
    aplica_modalidade: ModalidadeTarifaria | None = None
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None
    expressao_logica: dict | None = None
    ativa: bool = True

    @model_validator(mode="after")
    def validar_vigencia(self) -> "RegraValidacaoCreate":
        if self.vigencia_fim is not None and self.vigencia_inicio is None:
            raise ValueError("vigencia_inicio é obrigatória quando vigencia_fim é informada")
        if (
            self.vigencia_inicio is not None
            and self.vigencia_fim is not None
            and self.vigencia_fim < self.vigencia_inicio
        ):
            raise ValueError("vigencia_fim deve ser igual ou posterior a vigencia_inicio")
        return self


class RegraValidacaoUpdate(BaseModel):
    pacote_regras_id: uuid.UUID | None = None
    documento_origem_id: uuid.UUID | None = None
    codigo: str | None = Field(default=None, max_length=50)
    nome: str | None = Field(default=None, max_length=255)
    descricao: str | None = None
    categoria: CategoriaRegra | None = None
    severidade: Severidade | None = None
    aplica_grupo: Grupo | None = None
    aplica_subgrupo: Subgrupo | None = None
    aplica_modalidade: ModalidadeTarifaria | None = None
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None
    expressao_logica: dict | None = None
    ativa: bool | None = None


class RegraValidacaoOut(RegraValidacaoCreate):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
