import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from src.app.api.v1.dependencies import CurrentUserDep, DbDep
from src.app.domains.faturas.schemas import (
    FaturaCreate,
    FaturaDetalheOut,
    FaturasOut,
    FaturaUpdate,
    ItemFaturaCreate,
    ItemFaturaOut,
    ItemFaturaUpdate,
    MedidaFaturaCreate,
    MedidaFaturaOut,
    MedidaFaturaUpdate,
    TributoFaturaCreate,
    TributoFaturaOut,
    TributoFaturaUpdate,
)
from src.app.domains.faturas.service import FaturaService

router = APIRouter(tags=["Faturas"])


def get_fatura_service(db: DbDep) -> FaturaService:
    return FaturaService(db)


FaturaServiceDep = Annotated[FaturaService, Depends(get_fatura_service)]


@router.get("/", response_model=FaturasOut)
def listar_faturas(
    ator: CurrentUserDep,
    service: FaturaServiceDep,
    unidade_consumidora_id: Annotated[uuid.UUID | None, Query()] = None,
    lote_auditoria_id: Annotated[uuid.UUID | None, Query()] = None,
    competencia: Annotated[str | None, Query()] = None,
) -> FaturasOut:
    return service.listar(
        ator=ator,
        unidade_consumidora_id=unidade_consumidora_id,
        lote_auditoria_id=lote_auditoria_id,
        competencia=competencia,
    )


@router.post("/", response_model=FaturaDetalheOut, status_code=status.HTTP_201_CREATED)
def criar_fatura(
    payload: FaturaCreate,
    ator: CurrentUserDep,
    service: FaturaServiceDep,
) -> FaturaDetalheOut:
    return service.criar(payload, ator=ator)


@router.get("/{id}", response_model=FaturaDetalheOut)
def obter_fatura(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: FaturaServiceDep,
) -> FaturaDetalheOut:
    return service.obter(id, ator=ator)


@router.patch("/{id}", response_model=FaturaDetalheOut)
def atualizar_fatura(
    id: uuid.UUID,
    payload: FaturaUpdate,
    ator: CurrentUserDep,
    service: FaturaServiceDep,
) -> FaturaDetalheOut:
    service.atualizar(id, payload, ator=ator)
    return service.obter(id, ator=ator)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_fatura(id: uuid.UUID, ator: CurrentUserDep, service: FaturaServiceDep) -> Response:
    service.deletar(id, ator=ator)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{id}/medidas", response_model=list[MedidaFaturaOut])
def listar_medidas(
    id: uuid.UUID, ator: CurrentUserDep, service: FaturaServiceDep
) -> list[MedidaFaturaOut]:
    return service.listar_medidas(id, ator=ator)


@router.post("/{id}/medidas", response_model=MedidaFaturaOut, status_code=status.HTTP_201_CREATED)
def criar_medida(
    id: uuid.UUID,
    payload: MedidaFaturaCreate,
    ator: CurrentUserDep,
    service: FaturaServiceDep,
) -> MedidaFaturaOut:
    return service.criar_medida(id, payload, ator=ator)


@router.patch("/{id}/medidas/{medida_id}", response_model=MedidaFaturaOut)
def atualizar_medida(
    id: uuid.UUID,
    medida_id: uuid.UUID,
    payload: MedidaFaturaUpdate,
    ator: CurrentUserDep,
    service: FaturaServiceDep,
) -> MedidaFaturaOut:
    return service.atualizar_medida(id, medida_id, payload, ator=ator)


@router.delete("/{id}/medidas/{medida_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_medida(
    id: uuid.UUID,
    medida_id: uuid.UUID,
    ator: CurrentUserDep,
    service: FaturaServiceDep,
) -> Response:
    service.deletar_medida(id, medida_id, ator=ator)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{id}/itens", response_model=list[ItemFaturaOut])
def listar_itens(
    id: uuid.UUID, ator: CurrentUserDep, service: FaturaServiceDep
) -> list[ItemFaturaOut]:
    return service.listar_itens(id, ator=ator)


@router.post("/{id}/itens", response_model=ItemFaturaOut, status_code=status.HTTP_201_CREATED)
def criar_item(
    id: uuid.UUID,
    payload: ItemFaturaCreate,
    ator: CurrentUserDep,
    service: FaturaServiceDep,
) -> ItemFaturaOut:
    return service.criar_item(id, payload, ator=ator)


@router.patch("/{id}/itens/{item_id}", response_model=ItemFaturaOut)
def atualizar_item(
    id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ItemFaturaUpdate,
    ator: CurrentUserDep,
    service: FaturaServiceDep,
) -> ItemFaturaOut:
    return service.atualizar_item(id, item_id, payload, ator=ator)


@router.delete("/{id}/itens/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_item(
    id: uuid.UUID,
    item_id: uuid.UUID,
    ator: CurrentUserDep,
    service: FaturaServiceDep,
) -> Response:
    service.deletar_item(id, item_id, ator=ator)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{id}/tributos", response_model=list[TributoFaturaOut])
def listar_tributos(
    id: uuid.UUID, ator: CurrentUserDep, service: FaturaServiceDep
) -> list[TributoFaturaOut]:
    return service.listar_tributos(id, ator=ator)


@router.post("/{id}/tributos", response_model=TributoFaturaOut, status_code=status.HTTP_201_CREATED)
def criar_tributo(
    id: uuid.UUID,
    payload: TributoFaturaCreate,
    ator: CurrentUserDep,
    service: FaturaServiceDep,
) -> TributoFaturaOut:
    return service.criar_tributo(id, payload, ator=ator)


@router.patch("/{id}/tributos/{tributo_id}", response_model=TributoFaturaOut)
def atualizar_tributo(
    id: uuid.UUID,
    tributo_id: uuid.UUID,
    payload: TributoFaturaUpdate,
    ator: CurrentUserDep,
    service: FaturaServiceDep,
) -> TributoFaturaOut:
    return service.atualizar_tributo(id, tributo_id, payload, ator=ator)


@router.delete("/{id}/tributos/{tributo_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_tributo(
    id: uuid.UUID,
    tributo_id: uuid.UUID,
    ator: CurrentUserDep,
    service: FaturaServiceDep,
) -> Response:
    service.deletar_tributo(id, tributo_id, ator=ator)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
