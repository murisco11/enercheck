import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Query,
    Response,
    UploadFile,
    status,
)

from src.app.api.v1.dependencies import CurrentUserDep, DbDep
from src.app.core.enums import StatusExtracao
from src.app.domains.documental.processamento import processar_extracao
from src.app.domains.documental.schemas import (
    DocumentoBrutoCreate,
    DocumentoBrutoOut,
    DocumentoBrutoUpdate,
    DocumentosBrutosOut,
    LayoutFaturaCreate,
    LayoutFaturaOut,
    LayoutFaturaUpdate,
)
from src.app.domains.documental.service import DocumentoBrutoService, LayoutFaturaService

router = APIRouter(tags=["Documental"])


def get_layout_service(db: DbDep) -> LayoutFaturaService:
    return LayoutFaturaService(db)


def get_documento_service(db: DbDep) -> DocumentoBrutoService:
    return DocumentoBrutoService(db)


LayoutServiceDep = Annotated[LayoutFaturaService, Depends(get_layout_service)]
DocumentoServiceDep = Annotated[DocumentoBrutoService, Depends(get_documento_service)]


@router.get("/layouts", response_model=list[LayoutFaturaOut])
def listar_layouts(
    _: CurrentUserDep,
    service: LayoutServiceDep,
    distribuidora_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[LayoutFaturaOut]:
    return service.listar(distribuidora_id=distribuidora_id)


@router.post("/layouts", response_model=LayoutFaturaOut, status_code=status.HTTP_201_CREATED)
def criar_layout(
    payload: LayoutFaturaCreate,
    ator: CurrentUserDep,
    service: LayoutServiceDep,
) -> LayoutFaturaOut:
    return service.criar(payload, ator=ator)


@router.get("/layouts/{id}", response_model=LayoutFaturaOut)
def obter_layout(id: uuid.UUID, _: CurrentUserDep, service: LayoutServiceDep) -> LayoutFaturaOut:
    return service.obter(id)


@router.patch("/layouts/{id}", response_model=LayoutFaturaOut)
def atualizar_layout(
    id: uuid.UUID,
    payload: LayoutFaturaUpdate,
    ator: CurrentUserDep,
    service: LayoutServiceDep,
) -> LayoutFaturaOut:
    return service.atualizar(id, payload, ator=ator)


@router.delete("/layouts/{id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_layout(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: LayoutServiceDep,
    permanente: bool = Query(default=False, description="Se true, remove permanentemente do banco"),
) -> Response:
    service.deletar(id, ator=ator, permanente=permanente)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/documentos", response_model=DocumentosBrutosOut)
def listar_documentos(
    ator: CurrentUserDep,
    service: DocumentoServiceDep,
    unidade_consumidora_id: Annotated[uuid.UUID | None, Query()] = None,
    lote_auditoria_id: Annotated[uuid.UUID | None, Query()] = None,
    status_extracao: Annotated[StatusExtracao | None, Query()] = None,
) -> DocumentosBrutosOut:
    return service.listar(
        ator=ator,
        unidade_consumidora_id=unidade_consumidora_id,
        lote_auditoria_id=lote_auditoria_id,
        status_extracao=status_extracao,
    )


@router.post(
    "/documentos/upload",
    response_model=DocumentoBrutoOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_documento(
    ator: CurrentUserDep,
    service: DocumentoServiceDep,
    background: BackgroundTasks,
    arquivo: Annotated[UploadFile, File()],
    unidade_consumidora_id: Annotated[uuid.UUID, Form()],
    lote_auditoria_id: Annotated[uuid.UUID | None, Form()] = None,
) -> DocumentoBrutoOut:
    conteudo = await arquivo.read()
    documento = service.ingerir(
        conteudo=conteudo,
        nome_original=arquivo.filename or "documento.pdf",
        unidade_consumidora_id=unidade_consumidora_id,
        ator=ator,
        lote_auditoria_id=lote_auditoria_id,
    )
    background.add_task(processar_extracao, documento.id)
    return DocumentoBrutoOut.model_validate(documento)


@router.post("/documentos", response_model=DocumentoBrutoOut, status_code=status.HTTP_201_CREATED)
def criar_documento(
    payload: DocumentoBrutoCreate,
    ator: CurrentUserDep,
    service: DocumentoServiceDep,
) -> DocumentoBrutoOut:
    return service.criar(payload, ator=ator)


@router.get("/documentos/{id}", response_model=DocumentoBrutoOut)
def obter_documento(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: DocumentoServiceDep,
) -> DocumentoBrutoOut:
    return service.obter(id, ator=ator)


@router.patch("/documentos/{id}", response_model=DocumentoBrutoOut)
def atualizar_documento(
    id: uuid.UUID,
    payload: DocumentoBrutoUpdate,
    ator: CurrentUserDep,
    service: DocumentoServiceDep,
) -> DocumentoBrutoOut:
    return service.atualizar(id, payload, ator=ator)


@router.delete("/documentos/{id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_documento(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: DocumentoServiceDep,
) -> Response:
    service.deletar(id, ator=ator)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
