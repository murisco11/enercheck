import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from src.app.api.v1.dependencies import UsuarioAtualDep, UsuarioServiceDep, requer_papel
from src.app.core.enums import PapelUsuario
from src.app.domains.auth.schemas import (
    LoginRequest,
    TokenOut,
    UsuarioCreate,
    UsuarioOut,
    UsuariosOut,
    UsuarioUpdate,
)

router = APIRouter(tags=["Autenticação"])


@router.post("/token", response_model=TokenOut)
def token(payload: LoginRequest, service: UsuarioServiceDep) -> TokenOut:
    return service.login(payload)


@router.get("/me", response_model=UsuarioOut)
def me(usuario: UsuarioAtualDep, service: UsuarioServiceDep) -> UsuarioOut:
    return service.obter(usuario.id)


@router.post("/usuarios", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def registrar(payload: UsuarioCreate, service: UsuarioServiceDep) -> UsuarioOut:
    return service.registrar(payload)


@router.get("/usuarios", response_model=UsuariosOut)
def listar(
    _: Annotated[object, Depends(requer_papel(PapelUsuario.ADMIN))],
    service: UsuarioServiceDep,
) -> UsuariosOut:
    return service.listar()


@router.get("/usuarios/{id}", response_model=UsuarioOut)
def obter(
    id: uuid.UUID,
    usuario: UsuarioAtualDep,
    service: UsuarioServiceDep,
) -> UsuarioOut:
    if PapelUsuario(usuario.papel) != PapelUsuario.ADMIN and usuario.id != id:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito.")
    return service.obter(id)


@router.patch("/usuarios/{id}", response_model=UsuarioOut)
def atualizar(
    id: uuid.UUID,
    payload: UsuarioUpdate,
    usuario: UsuarioAtualDep,
    service: UsuarioServiceDep,
) -> UsuarioOut:
    return service.atualizar(id, payload, ator=usuario)


@router.delete("/usuarios/{id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(
    id: uuid.UUID,
    usuario: UsuarioAtualDep,
    service: UsuarioServiceDep,
    permanente: bool = Query(default=False, description="Se true, remove permanentemente do banco"),
) -> Response:
    service.deletar(id, ator=usuario, permanente=permanente)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
