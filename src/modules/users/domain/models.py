from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=255)
    cpf: str | None = Field(default=None, min_length=11, max_length=14)
    cnpj: str | None = Field(default=None, min_length=14, max_length=18)
    cep: str = Field(min_length=8, max_length=9)
    business: str | None = Field(default=None, min_length=1, max_length=255)


class UserUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=255)
    cpf: str | None = Field(default=None, min_length=11, max_length=14)
    cnpj: str | None = Field(default=None, min_length=14, max_length=18)
    cep: str = Field(min_length=8, max_length=9)
    business: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None


class UserRead(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    cpf: str | None
    cnpj: str | None
    cep: str
    business: str | None
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    items: list[UserRead]


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=255)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
