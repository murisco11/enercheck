import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from src.app.api.v1.dependencies import DbDep, CurrentUserDep, requer_papel
from src.app.core.enums import PapelUsuario
from src.app.domains.clientes.schemas import (
    ClienteCreate,
    ClienteOut,
    ClienteUpdate,
    ClientesOut,
    DistribuidoraCreate,
    DistribuidoraOut,
    LoteCreate,
    LoteOut,
    LoteResumoOut,
    LoteUpdate,
    PageKeysetOut,
    PaginacaoKeyset,
    UCsOut,
    UnidadeConsumidoraCreate,
    UnidadeConsumidoraOut,
    UnidadeConsumidoraUpdate,
)
from src.app.domains.clientes.service import ClienteService, DistribuidoraService, LoteService


distribuidoras_router = APIRouter(tags=["Distribuidoras"])


def get_distribuidora_service(db: DbDep) -> DistribuidoraService:
    return DistribuidoraService(db)


DistribuidoraServiceDep = Annotated[DistribuidoraService, Depends(get_distribuidora_service)]


@distribuidoras_router.get("/", response_model=list[DistribuidoraOut])
def listar_distribuidoras(
    _: CurrentUserDep,
    service: DistribuidoraServiceDep,
) -> list[DistribuidoraOut]:
    return service.listar()


@distribuidoras_router.post("/", response_model=DistribuidoraOut, status_code=status.HTTP_201_CREATED)
def criar_distribuidora(
    payload: DistribuidoraCreate,
    ator: CurrentUserDep,
    service: DistribuidoraServiceDep,
) -> DistribuidoraOut:
    return service.criar(payload, ator=ator)


@distribuidoras_router.get("/{id}", response_model=DistribuidoraOut)
def obter_distribuidora(
    id: uuid.UUID,
    _: CurrentUserDep,
    service: DistribuidoraServiceDep,
) -> DistribuidoraOut:
    return service.obter(id)


@distribuidoras_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_distribuidora(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: DistribuidoraServiceDep,
    permanente: bool = Query(default=False, description="Se true, remove permanentemente do banco"),
) -> Response:
    service.deletar(id, ator=ator, permanente=permanente)
    return Response(status_code=status.HTTP_204_NO_CONTENT)



clientes_router = APIRouter(tags=["Clientes"])


def get_cliente_service(db: DbDep) -> ClienteService:
    return ClienteService(db)


ClienteServiceDep = Annotated[ClienteService, Depends(get_cliente_service)]


@clientes_router.get("/", response_model=ClientesOut)
def listar_clientes(ator: CurrentUserDep, service: ClienteServiceDep) -> ClientesOut:
    return service.listar(ator=ator)


@clientes_router.post("/", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def criar_cliente(
    payload: ClienteCreate,
    ator: CurrentUserDep,
    service: ClienteServiceDep,
) -> ClienteOut:
    return service.criar(payload, ator=ator)


@clientes_router.get("/{id}", response_model=ClienteOut)
def obter_cliente(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: ClienteServiceDep,
) -> ClienteOut:
    return service.obter(id, ator=ator)


@clientes_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_cliente(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: ClienteServiceDep,
    permanente: bool = Query(default=False, description="Se true, remove permanentemente do banco"),
) -> Response:
    service.deletar(id, ator=ator, permanente=permanente)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@clientes_router.patch("/{id}", response_model=ClienteOut)
def atualizar_cliente(
    id: uuid.UUID,
    payload: ClienteUpdate,
    ator: CurrentUserDep,
    service: ClienteServiceDep,
) -> ClienteOut:
    return service.atualizar(id, payload, ator=ator)


@clientes_router.get("/{id}/ucs", response_model=UCsOut)
def listar_ucs(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: ClienteServiceDep,
) -> UCsOut:
    return service.listar_ucs(id, ator=ator)


@clientes_router.post("/{id}/ucs", response_model=UnidadeConsumidoraOut, status_code=status.HTTP_201_CREATED)
def criar_uc(
    id: uuid.UUID,
    payload: UnidadeConsumidoraCreate,
    ator: CurrentUserDep,
    service: ClienteServiceDep,
) -> UnidadeConsumidoraOut:
    return service.criar_uc(id, payload, ator=ator)


@clientes_router.get("/{id}/ucs/{uc_id}", response_model=UnidadeConsumidoraOut)
def obter_uc(
    id: uuid.UUID,
    uc_id: uuid.UUID,
    ator: CurrentUserDep,
    service: ClienteServiceDep,
) -> UnidadeConsumidoraOut:
    return service.obter_uc(id, uc_id, ator=ator)


@clientes_router.delete("/{id}/ucs/{uc_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_uc(
    id: uuid.UUID,
    uc_id: uuid.UUID,
    ator: CurrentUserDep,
    service: ClienteServiceDep,
    permanente: bool = Query(default=False, description="Se true, remove permanentemente do banco"),
) -> Response:
    service.deletar_uc(id, uc_id, ator=ator, permanente=permanente)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@clientes_router.patch("/{id}/ucs/{uc_id}", response_model=UnidadeConsumidoraOut)
def atualizar_uc(
    id: uuid.UUID,
    uc_id: uuid.UUID,
    payload: UnidadeConsumidoraUpdate,
    ator: CurrentUserDep,
    service: ClienteServiceDep,
) -> UnidadeConsumidoraOut:
    return service.atualizar_uc(id, uc_id, payload, ator=ator)



lotes_router = APIRouter(tags=["Lotes"])


def get_lote_service(db: DbDep) -> LoteService:
    return LoteService(db)


LoteServiceDep = Annotated[LoteService, Depends(get_lote_service)]


@lotes_router.get("/", response_model=PageKeysetOut[LoteResumoOut])
def listar_lotes(
    ator: CurrentUserDep,
    service: LoteServiceDep,
    uc_id: uuid.UUID | None = Query(default=None),
    after_id: uuid.UUID | None = Query(default=None),
    limite: int = Query(default=50, ge=1, le=200),
) -> PageKeysetOut[LoteResumoOut]:
    pag = PaginacaoKeyset(after_id=after_id, limite=limite)
    return service.listar(pag=pag, ator=ator, uc_id=uc_id)


@lotes_router.post("/", response_model=LoteOut, status_code=status.HTTP_201_CREATED)
def criar_lote(
    payload: LoteCreate,
    ator: CurrentUserDep,
    service: LoteServiceDep,
) -> LoteOut:
    return service.criar(payload, ator=ator)


@lotes_router.get("/{id}", response_model=LoteOut)
def obter_lote(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: LoteServiceDep,
) -> LoteOut:
    return service.obter(id, ator=ator)


@lotes_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_lote(
    id: uuid.UUID,
    ator: CurrentUserDep,
    service: LoteServiceDep,
    permanente: bool = Query(default=False, description="Se true, remove permanentemente do banco"),
) -> Response:
    service.deletar(id, ator=ator, permanente=permanente)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@lotes_router.patch("/{id}", response_model=LoteOut)
def atualizar_lote(
    id: uuid.UUID,
    payload: LoteUpdate,
    ator: CurrentUserDep,
    service: LoteServiceDep,
) -> LoteOut:
    return service.atualizar(id, payload, ator=ator)
