import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.app.core.enums import PapelUsuario


class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    senha: str = Field(min_length=8)
    papel: PapelUsuario = PapelUsuario.CONSULTOR


class UsuarioUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    senha: str | None = Field(default=None, min_length=8)
    papel: PapelUsuario | None = None
    ativo: bool | None = None


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    email: str
    papel: PapelUsuario
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime


class UsuarioResumoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    email: str
    papel: PapelUsuario
    ativo: bool


class UsuariosOut(BaseModel):
    itens: list[UsuarioResumoOut]


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    senha: str = Field(min_length=8)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario: UsuarioOut
