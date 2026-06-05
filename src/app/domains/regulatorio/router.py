import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from src.app.api.v1.dependencies import CurrentUserDep, DbDep, requer_papel
from src.app.core.enums import PapelUsuario
from src.app.domains.regulatorio.schemas import (
    ChunkCreate,
    ChunkOut,
    DocumentoRegulatorioCreate,
    DocumentoRegulatorioOut,
    DocumentoRegulatorioUpdate,
    PacoteRegrasCreate,
    PacoteRegrasOut,
    PacoteRegrasUpdate,
    RegraValidacaoCreate,
    RegraValidacaoOut,
    RegraValidacaoUpdate,
    SnapshotTarifaCreate,
    SnapshotTarifaOut,
    SnapshotTarifaUpdate,
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


@router.patch(
    "/documentos/{doc_id}",
    response_model=DocumentoRegulatorioOut,
    dependencies=[Depends(requer_papel(PapelUsuario.ADMIN))],
)
def atualizar_documento(doc_id: uuid.UUID, data: DocumentoRegulatorioUpdate, db: DbDep):
    return DocumentoRegulatorioService(db).atualizar(doc_id, data)


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


@router.get("/tarifas/snapshots", response_model=list[SnapshotTarifaOut])
def listar_snapshots(
    db: DbDep,
    _: CurrentUserDep,
    distribuidora_id: Annotated[uuid.UUID | None, Query()] = None,
):
    return SnapshotTarifaService(db).listar(distribuidora_id=distribuidora_id)


@router.post(
    "/tarifas/snapshots",
    response_model=SnapshotTarifaOut,
    status_code=201,
    dependencies=[Depends(requer_papel(PapelUsuario.ADMIN))],
)
def criar_snapshot(data: SnapshotTarifaCreate, db: DbDep):
    return SnapshotTarifaService(db).criar(data)


@router.get("/tarifas/snapshots/{snap_id}", response_model=SnapshotTarifaOut)
def buscar_snapshot(snap_id: uuid.UUID, db: DbDep, _: CurrentUserDep):
    return SnapshotTarifaService(db).buscar(snap_id)


@router.patch(
    "/tarifas/snapshots/{snap_id}",
    response_model=SnapshotTarifaOut,
    dependencies=[Depends(requer_papel(PapelUsuario.ADMIN))],
)
def atualizar_snapshot(snap_id: uuid.UUID, data: SnapshotTarifaUpdate, db: DbDep):
    return SnapshotTarifaService(db).atualizar(snap_id, data)


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


@router.get("/regras/pacotes/{pacote_id}", response_model=PacoteRegrasOut)
def buscar_pacote(pacote_id: uuid.UUID, db: DbDep, _: CurrentUserDep):
    return PacoteRegrasService(db).buscar(pacote_id)


@router.patch(
    "/regras/pacotes/{pacote_id}",
    response_model=PacoteRegrasOut,
    dependencies=[Depends(requer_papel(PapelUsuario.ADMIN))],
)
def atualizar_pacote(pacote_id: uuid.UUID, data: PacoteRegrasUpdate, db: DbDep):
    return PacoteRegrasService(db).atualizar(pacote_id, data)


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


@router.get("/regras/{regra_id}", response_model=RegraValidacaoOut)
def buscar_regra(regra_id: uuid.UUID, db: DbDep, _: CurrentUserDep):
    return PacoteRegrasService(db).buscar_regra(regra_id)


@router.patch(
    "/regras/{regra_id}",
    response_model=RegraValidacaoOut,
    dependencies=[Depends(requer_papel(PapelUsuario.ADMIN))],
)
def atualizar_regra(regra_id: uuid.UUID, data: RegraValidacaoUpdate, db: DbDep):
    return PacoteRegrasService(db).atualizar_regra(regra_id, data)


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
