import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status

from src.app.api.v1.dependencies import CurrentUserDep, DbDep
from src.app.core.enums import StatusAchado
from src.app.domains.auditoria.processamento import processar_validacao_lote
from src.app.domains.auditoria.schemas import (
    AchadoCreate,
    AchadoOut,
    AchadosOut,
    AchadoUpdate,
    ExecucaoValidacaoDetalheOut,
    ExecucaoValidacaoOut,
)
from src.app.domains.auditoria.service import AchadoService, ValidacaoService

validacoes_router = APIRouter(tags=["Validações"])
achados_router = APIRouter(tags=["Achados"])


def get_validacao_service(db: DbDep) -> ValidacaoService:
    return ValidacaoService(db)


def get_achado_service(db: DbDep) -> AchadoService:
    return AchadoService(db)


ValidacaoServiceDep = Annotated[ValidacaoService, Depends(get_validacao_service)]
AchadoServiceDep = Annotated[AchadoService, Depends(get_achado_service)]


@validacoes_router.get("/{id}", response_model=ExecucaoValidacaoDetalheOut)
def obter_validacao(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: ValidacaoServiceDep,
) -> ExecucaoValidacaoDetalheOut:
    return service.obter(id, ator=ator)


@achados_router.get("/", response_model=AchadosOut)
def listar_achados(
    ator: CurrentUserDep,
    service: AchadoServiceDep,
    fatura_id: Annotated[uuid.UUID | None, Query()] = None,
    status_achado: Annotated[StatusAchado | None, Query(alias="status")] = None,
) -> AchadosOut:
    return service.listar(ator=ator, fatura_id=fatura_id, status=status_achado)


@achados_router.post("/", response_model=AchadoOut, status_code=status.HTTP_201_CREATED)
def criar_achado(
    payload: AchadoCreate,
    ator: CurrentUserDep,
    service: AchadoServiceDep,
) -> AchadoOut:
    return service.criar(payload, ator=ator)


@achados_router.get("/{id}", response_model=AchadoOut)
def obter_achado(id: uuid.UUID, ator: CurrentUserDep, service: AchadoServiceDep) -> AchadoOut:
    return service.obter(id, ator=ator)


@achados_router.patch("/{id}", response_model=AchadoOut)
def atualizar_achado(
    id: uuid.UUID,
    payload: AchadoUpdate,
    ator: CurrentUserDep,
    service: AchadoServiceDep,
) -> AchadoOut:
    return service.atualizar(id, payload, ator=ator)


@achados_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_achado(id: uuid.UUID, ator: CurrentUserDep, service: AchadoServiceDep) -> Response:
    service.deletar(id, ator=ator)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


fatura_validacoes_router = APIRouter(tags=["Validações"])


@fatura_validacoes_router.get("/{id}/validacoes", response_model=list[ExecucaoValidacaoOut])
def listar_validacoes_fatura(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: ValidacaoServiceDep,
) -> list[ExecucaoValidacaoOut]:
    return service.listar_por_fatura(id, ator=ator)


@fatura_validacoes_router.post(
    "/{id}/validacoes",
    response_model=ExecucaoValidacaoDetalheOut,
    status_code=status.HTTP_201_CREATED,
)
def executar_validacao_fatura(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: ValidacaoServiceDep,
) -> ExecucaoValidacaoDetalheOut:
    return service.executar(id, ator=ator)


lote_validacoes_router = APIRouter(tags=["Validações"])


@lote_validacoes_router.post("/{id}/validacoes", status_code=status.HTTP_202_ACCEPTED)
def executar_validacao_lote(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: ValidacaoServiceDep,
    background: BackgroundTasks,
) -> dict[str, str]:
    lote_id = service.autorizar_lote(id, ator=ator)
    background.add_task(processar_validacao_lote, lote_id, ator.id)
    return {"detail": "Validação do lote agendada.", "lote_id": str(lote_id)}
