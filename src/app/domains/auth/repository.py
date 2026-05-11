import hashlib
import secrets
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.app.core.enums import PapelUsuario
from src.app.domains.auth.models import Usuario
from src.app.domains.auth.schemas import UsuarioCreate, UsuarioUpdate


@dataclass(slots=True)
class CredenciaisUsuario:
    id: uuid.UUID
    senha_hash: str
    papel: PapelUsuario
    ativo: bool


class UsuarioRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def count(self) -> int:
        return int(self.db.scalar(select(func.count()).select_from(Usuario)) or 0)

    def criar(self, dados: UsuarioCreate, papel: PapelUsuario) -> Usuario:
        usuario = Usuario(
            nome=dados.nome,
            email=dados.email,
            senha_hash=self._hash_senha(dados.senha),
            papel=papel,
            ativo=True,
        )
        self.db.add(usuario)
        self.db.flush()
        return usuario

    def listar(self) -> list[Usuario]:
        return list(self.db.scalars(select(Usuario).order_by(Usuario.criado_em)).all())

    def buscar_por_id(self, id: uuid.UUID) -> Usuario | None:
        return self.db.get(Usuario, id)

    def buscar_credenciais_por_email(self, email: str) -> CredenciaisUsuario | None:
        usuario = self.db.scalar(select(Usuario).where(Usuario.email == email))
        if usuario is None:
            return None
        return CredenciaisUsuario(
            id=usuario.id,
            senha_hash=usuario.senha_hash,
            papel=usuario.papel,
            ativo=usuario.ativo,
        )

    def atualizar(self, usuario: Usuario, dados: UsuarioUpdate, ator_papel: PapelUsuario) -> None:
        if dados.nome is not None:
            usuario.nome = dados.nome
        if dados.email is not None:
            usuario.email = dados.email
        if dados.senha is not None:
            usuario.senha_hash = self._hash_senha(dados.senha)
        if dados.papel is not None and ator_papel == PapelUsuario.ADMIN:
            usuario.papel = dados.papel
        if dados.ativo is not None and ator_papel == PapelUsuario.ADMIN:
            usuario.ativo = dados.ativo
        self.db.flush()

    def desativar(self, usuario: Usuario) -> None:
        usuario.ativo = False
        self.db.flush()

    def remover(self, usuario: Usuario) -> None:
        self.db.delete(usuario)
        self.db.flush()

    def verificar_senha(self, senha: str, senha_hash: str) -> bool:
        try:
            salt, hashed = senha_hash.split("$", maxsplit=1)
        except ValueError:
            return False
        candidato = hashlib.pbkdf2_hmac(
            "sha256", senha.encode("utf-8"), salt.encode("utf-8"), 100_000
        ).hex()
        return secrets.compare_digest(candidato, hashed)

    @staticmethod
    def _hash_senha(senha: str) -> str:
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return f"{salt}${hashed.hex()}"
