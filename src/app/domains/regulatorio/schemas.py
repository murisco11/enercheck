import uuid
from datetime import date

from pydantic import BaseModel, Field

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


class DocumentoRegulatorioOut(DocumentoRegulatorioCreate):
    id: uuid.UUID
    criado_em: date

    model_config = {"from_attributes": True}



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


class BuscaSimilaridadeQuery(BaseModel):
    texto: str = Field(min_length=3, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    documento_id: uuid.UUID | None = None


class ChunkSimilarOut(ChunkOut):
    similaridade: float



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
    valor_tusd: float
    valor_te: float
    valor_tusd_com_tributos: float
    valor_te_com_tributos: float
    adicional_bandeira: float = 0.0
    resolucao_origem: str | None = None


class SnapshotTarifaOut(SnapshotTarifaCreate):
    id: uuid.UUID

    model_config = {"from_attributes": True}



class PacoteRegrasCreate(BaseModel):
    versao: str = Field(max_length=50)
    descricao: str | None = None
    vigente: bool = False


class PacoteRegrasOut(PacoteRegrasCreate):
    id: uuid.UUID
    publicado_por_id: uuid.UUID | None

    model_config = {"from_attributes": True}



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


class RegraValidacaoOut(RegraValidacaoCreate):
    id: uuid.UUID

    model_config = {"from_attributes": True}
