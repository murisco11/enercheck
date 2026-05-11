import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app.core.enums import PapelUsuario
from src.app.core.exceptions import (
    AcessoNegadoError,
    ConflitoDuplicidadeError,
    CredenciaisInvalidasError,
    NaoEncontradoError,
)
from src.app.core.security import TokenService
from src.app.domains.auth.models import Usuario
from src.app.domains.auth.repository import UsuarioRepository
from src.app.domains.auth.schemas import (
    LoginRequest,
    TokenOut,
    UsuarioCreate,
    UsuarioOut,
    UsuarioResumoOut,
    UsuariosOut,
    UsuarioUpdate,
)


@dataclass(slots=True)
class UsuarioAutenticado:
    id: uuid.UUID
    email: str
    nome: str
    papel: str


class UsuarioService:
    def __init__(self, db: Session, token_service: TokenService) -> None:
        self.db = db
        self.repo = UsuarioRepository(db)
        self._token_service = token_service

    def registrar(self, dados: UsuarioCreate) -> UsuarioOut:
        count = self.repo.count()
        papel = PapelUsuario.ADMIN if count == 0 else dados.papel
        try:
            usuario = self.repo.criar(dados, papel=papel)
            self.db.commit()
            self.db.refresh(usuario)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflitoDuplicidadeError("Já existe um usuário com este e-mail.") from exc
        return UsuarioOut.model_validate(usuario)

    def login(self, dados: LoginRequest) -> TokenOut:
        credenciais = self.repo.buscar_credenciais_por_email(dados.email)
        if credenciais is None or not self.repo.verificar_senha(dados.senha, credenciais.senha_hash):
            raise CredenciaisInvalidasError("E-mail ou senha inválidos.")
        if not credenciais.ativo:
            raise CredenciaisInvalidasError("Conta inativa.")
        usuario = self._obter_orm(credenciais.id)
        token = self._token_service.create_token(subject=str(usuario.id), role=usuario.papel.value)
        expires_in = self._token_service._expire_minutes * 60
        return TokenOut(
            access_token=token,
            expires_in=expires_in,
            usuario=UsuarioOut.model_validate(usuario),
        )

    def listar(self) -> UsuariosOut:
        return UsuariosOut(itens=[UsuarioResumoOut.model_validate(u) for u in self.repo.listar()])

    def obter(self, id: uuid.UUID) -> UsuarioOut:
        return UsuarioOut.model_validate(self._obter_orm(id))

    def obter_autenticado(self, id: uuid.UUID) -> UsuarioAutenticado:
        usuario = self._obter_orm(id)
        if not usuario.ativo:
            raise CredenciaisInvalidasError("Conta inativa.")
        return UsuarioAutenticado(
            id=usuario.id,
            email=usuario.email,
            nome=usuario.nome,
            papel=usuario.papel.value,
        )

    def atualizar(self, id: uuid.UUID, dados: UsuarioUpdate, ator: UsuarioAutenticado) -> UsuarioOut:
        ator_papel = PapelUsuario(ator.papel)
        if ator_papel != PapelUsuario.ADMIN and ator.id != id:
            raise AcessoNegadoError("Você não pode alterar outro usuário.")
        usuario = self._obter_orm(id)
        try:
            self.repo.atualizar(usuario, dados, ator_papel=ator_papel)
            self.db.commit()
            self.db.refresh(usuario)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflitoDuplicidadeError("Já existe um usuário com este e-mail.") from exc
        return UsuarioOut.model_validate(usuario)

    def deletar(self, id: uuid.UUID, ator: UsuarioAutenticado, permanente: bool = False) -> None:
        if PapelUsuario(ator.papel) != PapelUsuario.ADMIN and ator.id != id:
            raise AcessoNegadoError("Você não pode excluir outro usuário.")
        if permanente and PapelUsuario(ator.papel) != PapelUsuario.ADMIN:
            raise AcessoNegadoError("Apenas administradores podem excluir permanentemente.")
        usuario = self._obter_orm(id)
        if permanente:
            self.repo.remover(usuario)
        else:
            self.repo.desativar(usuario)
        self.db.commit()

    def _obter_orm(self, id: uuid.UUID) -> Usuario:
        usuario = self.repo.buscar_por_id(id)
        if usuario is None:
            raise NaoEncontradoError("Usuário não encontrado.")
        return usuario
