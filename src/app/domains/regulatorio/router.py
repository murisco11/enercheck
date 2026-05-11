import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from src.app.api.v1.dependencies import CurrentUserDep, DbDep, get_current_user, requer_papel
from src.app.core.enums import PapelUsuario
from src.app.domains.auth.models import Usuario
from src.app.domains.regulatorio.schemas import (
    BuscaSimilaridadeQuery,
    ChunkCreate,
    ChunkOut,
    ChunkSimilarOut,
    DocumentoRegulatorioCreate,
    DocumentoRegulatorioOut,
    PacoteRegrasCreate,
    PacoteRegrasOut,
    RegraValidacaoCreate,
    RegraValidacaoOut,
    SnapshotTarifaCreate,
    SnapshotTarifaOut,
)
from src.app.domains.regulatorio.service import (
    ChunkService,
    DocumentoRegulatorioService,
    PacoteRegrasService,
    SnapshotTarifaService,
)

router = APIRouter()


@router.post(
    "/documentos",
    response_model=DocumentoRegulatorioOut,
    status_code=201,
    dependencies=[Depends(requer_papel(PapelUsuario.ADMIN))],
)
def criar_documento(data: DocumentoRegulatorioCreate, db: DbDep):
    return DocumentoRegulatorioService(db).criar(data)


@router.get("/documentos", response_model=list[DocumentoRegulatorioOut])
def listar_documentos(db: DbDep, _: CurrentUserDep):
    return DocumentoRegulatorioService(db).listar()


@router.get("/documentos/{doc_id}", response_model=DocumentoRegulatorioOut)
def buscar_documento(doc_id: uuid.UUID, db: DbDep, _: CurrentUserDep):
    return DocumentoRegulatorioService(db).buscar(doc_id)


@router.delete(
    "/documentos/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(requer_papel(PapelUsuario.ADMIN))],
)
def deletar_documento(
    doc_id: uuid.UUID,
    db: DbDep,
    permanente: bool = Query(default=False, description="Se true, remove permanentemente do banco"),
) -> Response:
    DocumentoRegulatorioService(db).deletar(doc_id, permanente=permanente)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/documentos/{doc_id}/chunks",
    response_model=list[ChunkOut],
    status_code=201,
    dependencies=[Depends(requer_papel(PapelUsuario.ADMIN))],
)
def adicionar_chunks(doc_id: uuid.UUID, chunks: list[ChunkCreate], db: DbDep):
    return ChunkService(db).adicionar_chunks(doc_id, chunks)


@router.get("/documentos/{doc_id}/chunks", response_model=list[ChunkOut])
def listar_chunks(doc_id: uuid.UUID, db: DbDep, _: CurrentUserDep):
    return ChunkService(db).listar_por_documento(doc_id)


@router.patch(
    "/chunks/{chunk_id}/embedding",
    status_code=204,
    dependencies=[Depends(requer_papel(PapelUsuario.ADMIN))],
)
def atualizar_embedding(chunk_id: uuid.UUID, embedding: list[float], db: DbDep):
    ChunkService(db).atualizar_embedding(chunk_id, embedding)


@router.post("/chunks/buscar", response_model=list[ChunkSimilarOut])
def buscar_similares(query: BuscaSimilaridadeQuery, db: DbDep, _: CurrentUserDep):
    """Busca semântica por similaridade de cosseno via pgvector.
    Integre um provedor de embeddings antes de usar este endpoint.
    Exemplo com OpenAI:

        vec = OpenAI().embeddings.create(
            model="text-embedding-3-small", input=query.texto
        ).data[0].embedding
        return ChunkService(db).buscar_similares(query, vec)
    """
    raise NotImplementedError(
        "Conecte um provedor de embeddings (OpenAI, Cohere, etc.) antes de usar este endpoint."
    )


@router.post(
    "/tarifas/snapshots",
    response_model=SnapshotTarifaOut,
    status_code=201,
    dependencies=[Depends(requer_papel(PapelUsuario.ADMIN))],
)
def criar_snapshot(data: SnapshotTarifaCreate, db: DbDep):
    return SnapshotTarifaService(db).criar(data)


@router.delete(
    "/tarifas/snapshots/{snap_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(requer_papel(PapelUsuario.ADMIN))],
)
def deletar_snapshot(
    snap_id: uuid.UUID,
    db: DbDep,
    permanente: bool = Query(default=False, description="Se true, remove permanentemente do banco"),
) -> Response:
    SnapshotTarifaService(db).deletar(snap_id, permanente=permanente)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tarifas/snapshots/vigentes", response_model=list[SnapshotTarifaOut])
def buscar_snapshots_vigentes(
    distribuidora_id: uuid.UUID,
    data_referencia: date,
    db: DbDep,
    _: CurrentUserDep,
):
    return SnapshotTarifaService(db).buscar_vigente(distribuidora_id, data_referencia)


@router.post(
    "/regras/pacotes",
    response_model=PacoteRegrasOut,
    status_code=201,
    dependencies=[Depends(requer_papel(PapelUsuario.ADMIN))],
)
def criar_pacote(data: PacoteRegrasCreate, db: DbDep, usuario: CurrentUserDep):
    return PacoteRegrasService(db).criar(data, usuario.id)


@router.get("/regras/pacotes", response_model=list[PacoteRegrasOut])
def listar_pacotes(db: DbDep, _: CurrentUserDep):
    return PacoteRegrasService(db).listar()


@router.delete(
    "/regras/pacotes/{pacote_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(requer_papel(PapelUsuario.ADMIN))],
)
def deletar_pacote(
    pacote_id: uuid.UUID,
    db: DbDep,
    permanente: bool = Query(default=False, description="Se true, remove permanentemente do banco"),
) -> Response:
    PacoteRegrasService(db).deletar_pacote(pacote_id, permanente=permanente)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/regras",
    response_model=RegraValidacaoOut,
    status_code=201,
    dependencies=[Depends(requer_papel(PapelUsuario.ADMIN))],
)
def criar_regra(data: RegraValidacaoCreate, db: DbDep):
    return PacoteRegrasService(db).adicionar_regra(data)


@router.get("/regras/pacotes/{pacote_id}/regras", response_model=list[RegraValidacaoOut])
def listar_regras(
    pacote_id: uuid.UUID,
    db: DbDep,
    _: CurrentUserDep,
    apenas_ativas: bool = True,
):
    return PacoteRegrasService(db).listar_regras(pacote_id, apenas_ativas)


@router.delete(
    "/regras/{regra_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(requer_papel(PapelUsuario.ADMIN))],
)
def deletar_regra(
    regra_id: uuid.UUID,
    db: DbDep,
    permanente: bool = Query(default=False, description="Se true, remove permanentemente do banco"),
) -> Response:
    PacoteRegrasService(db).deletar_regra(regra_id, permanente=permanente)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
