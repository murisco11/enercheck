import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from src.app.api.v1.dependencies import CurrentUserDep, DbDep
from src.app.core.enums import StatusRecuperacao
from src.app.domains.recuperacao.schemas import (
    CasoRecuperacaoCreate,
    CasoRecuperacaoDetalheOut,
    CasoRecuperacaoUpdate,
    CasosRecuperacaoOut,
    ItemRecuperacaoCreate,
    ItemRecuperacaoOut,
    ItemRecuperacaoUpdate,
)
from src.app.domains.recuperacao.service import RecuperacaoService

router = APIRouter(tags=["Recuperação"])


def get_recuperacao_service(db: DbDep) -> RecuperacaoService:
    return RecuperacaoService(db)


RecuperacaoServiceDep = Annotated[RecuperacaoService, Depends(get_recuperacao_service)]


@router.get("/casos", response_model=CasosRecuperacaoOut)
def listar_casos(
    ator: CurrentUserDep,
    service: RecuperacaoServiceDep,
    cliente_id: Annotated[uuid.UUID | None, Query()] = None,
    unidade_consumidora_id: Annotated[uuid.UUID | None, Query()] = None,
    status_recuperacao: Annotated[StatusRecuperacao | None, Query(alias="status")] = None,
) -> CasosRecuperacaoOut:
    return service.listar(
        ator=ator,
        cliente_id=cliente_id,
        unidade_consumidora_id=unidade_consumidora_id,
        status=status_recuperacao,
    )


@router.post(
    "/casos",
    response_model=CasoRecuperacaoDetalheOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_caso(
    payload: CasoRecuperacaoCreate,
    ator: CurrentUserDep,
    service: RecuperacaoServiceDep,
) -> CasoRecuperacaoDetalheOut:
    return service.criar(payload, ator=ator)


@router.get("/casos/{id}", response_model=CasoRecuperacaoDetalheOut)
def obter_caso(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: RecuperacaoServiceDep,
) -> CasoRecuperacaoDetalheOut:
    return service.obter(id, ator=ator)


@router.patch("/casos/{id}", response_model=CasoRecuperacaoDetalheOut)
def atualizar_caso(
    id: uuid.UUID,
    payload: CasoRecuperacaoUpdate,
    ator: CurrentUserDep,
    service: RecuperacaoServiceDep,
) -> CasoRecuperacaoDetalheOut:
    return service.atualizar(id, payload, ator=ator)


@router.delete("/casos/{id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_caso(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: RecuperacaoServiceDep,
) -> Response:
    service.deletar(id, ator=ator)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/casos/{id}/itens", response_model=list[ItemRecuperacaoOut])
def listar_itens(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: RecuperacaoServiceDep,
) -> list[ItemRecuperacaoOut]:
    return service.listar_itens(id, ator=ator)


@router.post(
    "/casos/{id}/itens",
    response_model=ItemRecuperacaoOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_item(
    id: uuid.UUID,
    payload: ItemRecuperacaoCreate,
    ator: CurrentUserDep,
    service: RecuperacaoServiceDep,
) -> ItemRecuperacaoOut:
    return service.criar_item(id, payload, ator=ator)


@router.patch("/casos/{id}/itens/{item_id}", response_model=ItemRecuperacaoOut)
def atualizar_item(
    id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ItemRecuperacaoUpdate,
    ator: CurrentUserDep,
    service: RecuperacaoServiceDep,
) -> ItemRecuperacaoOut:
    return service.atualizar_item(id, item_id, payload, ator=ator)


@router.delete("/casos/{id}/itens/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_item(
    id: uuid.UUID,
    item_id: uuid.UUID,
    ator: CurrentUserDep,
    service: RecuperacaoServiceDep,
) -> Response:
    service.deletar_item(id, item_id, ator=ator)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
