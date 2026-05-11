import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app.core.enums import PapelUsuario, StatusLote
from src.app.core.exceptions import (
    AcessoNegadoError,
    ConflitoDuplicidadeError,
    NaoEncontradoError,
    RegraVioladaError,
)
from src.app.domains.auth.service import UsuarioAutenticado
from src.app.domains.clientes.models import (
    AcessoCliente,
    Cliente,
    Distribuidora,
    LoteAuditoria,
    UnidadeConsumidora,
)
from src.app.domains.clientes.repository import (
    AcessoClienteRepository,
    ClienteRepository,
    DistribuidoraRepository,
    LoteRepository,
    UnidadeConsumidoraRepository,
)
from src.app.domains.clientes.schemas import (
    ClienteCreate,
    ClienteOut,
    ClienteResumoOut,
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
    UnidadeConsumidoraResumoOut,
    UnidadeConsumidoraUpdate,
)


class DistribuidoraService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DistribuidoraRepository(db)

    def deletar(self, id: uuid.UUID, ator: UsuarioAutenticado, permanente: bool = False) -> None:
        if PapelUsuario(ator.papel) != PapelUsuario.ADMIN:
            raise AcessoNegadoError("Apenas administradores podem excluir distribuidoras.")
        dist = self._obter_orm(id)
        if permanente:
            self.repo.remover(dist)
        else:
            self.repo.desativar(dist)
        self.db.commit()

    def criar(self, dados: DistribuidoraCreate, ator: UsuarioAutenticado) -> DistribuidoraOut:
        if PapelUsuario(ator.papel) != PapelUsuario.ADMIN:
            raise AcessoNegadoError("Apenas administradores podem cadastrar distribuidoras.")
        try:
            dist = self.repo.criar(dados)
            self.db.commit()
            self.db.refresh(dist)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflitoDuplicidadeError("Já existe uma distribuidora com este CNPJ.") from exc
        return DistribuidoraOut.model_validate(dist)

    def listar(self) -> list[DistribuidoraOut]:
        return [DistribuidoraOut.model_validate(d) for d in self.repo.listar()]

    def obter(self, id: uuid.UUID) -> DistribuidoraOut:
        return DistribuidoraOut.model_validate(self._obter_orm(id))

    def _obter_orm(self, id: uuid.UUID) -> Distribuidora:
        dist = self.repo.buscar_por_id(id)
        if dist is None:
            raise NaoEncontradoError("Distribuidora não encontrada.")
        return dist


class ClienteService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ClienteRepository(db)
        self.acesso_repo = AcessoClienteRepository(db)
        self.uc_repo = UnidadeConsumidoraRepository(db)

    def criar(self, dados: ClienteCreate, ator: UsuarioAutenticado) -> ClienteOut:
        if PapelUsuario(ator.papel) != PapelUsuario.ADMIN:
            raise AcessoNegadoError("Apenas administradores podem cadastrar clientes.")
        try:
            cliente = self.repo.criar(dados)
            self.db.commit()
            self.db.refresh(cliente)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflitoDuplicidadeError("Já existe um cliente com este CNPJ.") from exc
        return ClienteOut.model_validate(cliente)

    def listar(self, ator: UsuarioAutenticado) -> ClientesOut:
        if PapelUsuario(ator.papel) == PapelUsuario.ADMIN:
            clientes = self.repo.listar_todos()
        else:
            clientes = self.repo.listar_por_usuario(ator.id)
        return ClientesOut(
            itens=[ClienteResumoOut.model_validate(c) for c in clientes],
            total=len(clientes),
        )

    def obter(self, id: uuid.UUID, ator: UsuarioAutenticado) -> ClienteOut:
        self._verificar_acesso(id, ator)
        return ClienteOut.model_validate(self._obter_orm(id))

    def atualizar(
        self, id: uuid.UUID, dados, ator: UsuarioAutenticado
    ) -> ClienteOut:
        acesso = self._verificar_acesso(id, ator)
        if PapelUsuario(ator.papel) != PapelUsuario.ADMIN:
            if acesso is None or not acesso.pode_editar:
                raise AcessoNegadoError("Você não tem permissão para editar este cliente.")
        cliente = self._obter_orm(id)
        self.repo.atualizar(cliente, dados)
        self.db.commit()
        self.db.refresh(cliente)
        return ClienteOut.model_validate(cliente)

    def deletar(self, id: uuid.UUID, ator: UsuarioAutenticado, permanente: bool = False) -> None:
        acesso = self._verificar_acesso(id, ator)
        if PapelUsuario(ator.papel) != PapelUsuario.ADMIN:
            if acesso is None or not acesso.pode_editar:
                raise AcessoNegadoError("Você não tem permissão para excluir este cliente.")
        if permanente and PapelUsuario(ator.papel) != PapelUsuario.ADMIN:
            raise AcessoNegadoError("Apenas administradores podem excluir permanentemente.")
        cliente = self._obter_orm(id)
        if permanente:
            self.repo.remover(cliente)
        else:
            self.repo.desativar(cliente)
        self.db.commit()

    def criar_uc(
        self, cliente_id: uuid.UUID, dados: UnidadeConsumidoraCreate, ator: UsuarioAutenticado
    ) -> UnidadeConsumidoraOut:
        acesso = self._verificar_acesso(cliente_id, ator)
        if PapelUsuario(ator.papel) != PapelUsuario.ADMIN:
            if acesso is None or not acesso.pode_editar:
                raise AcessoNegadoError("Você não tem permissão para criar UCs neste cliente.")
        self._obter_orm(cliente_id)
        try:
            uc = self.uc_repo.criar(cliente_id, dados)
            self.db.commit()
            self.db.refresh(uc)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflitoDuplicidadeError(
                "Já existe uma UC com este código de instalação nesta distribuidora."
            ) from exc
        return UnidadeConsumidoraOut.model_validate(uc)

    def listar_ucs(self, cliente_id: uuid.UUID, ator: UsuarioAutenticado) -> UCsOut:
        self._verificar_acesso(cliente_id, ator)
        self._obter_orm(cliente_id)
        ucs = self.uc_repo.listar_por_cliente(cliente_id)
        return UCsOut(
            itens=[UnidadeConsumidoraResumoOut.model_validate(u) for u in ucs],
            total=len(ucs),
        )

    def obter_uc(
        self, cliente_id: uuid.UUID, uc_id: uuid.UUID, ator: UsuarioAutenticado
    ) -> UnidadeConsumidoraOut:
        self._verificar_acesso(cliente_id, ator)
        uc = self._obter_uc_orm(uc_id, cliente_id)
        return UnidadeConsumidoraOut.model_validate(uc)

    def atualizar_uc(
        self,
        cliente_id: uuid.UUID,
        uc_id: uuid.UUID,
        dados: UnidadeConsumidoraUpdate,
        ator: UsuarioAutenticado,
    ) -> UnidadeConsumidoraOut:
        acesso = self._verificar_acesso(cliente_id, ator)
        if PapelUsuario(ator.papel) != PapelUsuario.ADMIN:
            if acesso is None or not acesso.pode_editar:
                raise AcessoNegadoError("Você não tem permissão para editar UCs neste cliente.")
        uc = self._obter_uc_orm(uc_id, cliente_id)
        try:
            self.uc_repo.atualizar(uc, dados)
            self.db.commit()
            self.db.refresh(uc)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflitoDuplicidadeError(
                "Já existe uma UC com este código de instalação nesta distribuidora."
            ) from exc
        return UnidadeConsumidoraOut.model_validate(uc)

    def deletar_uc(
        self,
        cliente_id: uuid.UUID,
        uc_id: uuid.UUID,
        ator: UsuarioAutenticado,
        permanente: bool = False,
    ) -> None:
        acesso = self._verificar_acesso(cliente_id, ator)
        if PapelUsuario(ator.papel) != PapelUsuario.ADMIN:
            if acesso is None or not acesso.pode_editar:
                raise AcessoNegadoError("Você não tem permissão para excluir UCs deste cliente.")
        if permanente and PapelUsuario(ator.papel) != PapelUsuario.ADMIN:
            raise AcessoNegadoError("Apenas administradores podem excluir permanentemente.")
        uc = self._obter_uc_orm(uc_id, cliente_id)
        if permanente:
            self.uc_repo.remover(uc)
        else:
            self.uc_repo.desativar(uc)
        self.db.commit()

    def _verificar_acesso(
        self, cliente_id: uuid.UUID, ator: UsuarioAutenticado
    ) -> AcessoCliente | None:
        if PapelUsuario(ator.papel) == PapelUsuario.ADMIN:
            return None
        acesso = self.acesso_repo.buscar(usuario_id=ator.id, cliente_id=cliente_id)
        if acesso is None:
            raise AcessoNegadoError("Acesso não autorizado.")
        return acesso

    def _obter_orm(self, id: uuid.UUID) -> Cliente:
        cliente = self.repo.buscar_por_id(id)
        if cliente is None:
            raise NaoEncontradoError("Cliente não encontrado.")
        return cliente

    def _obter_uc_orm(self, uc_id: uuid.UUID, cliente_id: uuid.UUID) -> UnidadeConsumidora:
        uc = self.uc_repo.buscar_por_id(uc_id)
        if uc is None or uc.cliente_id != cliente_id:
            raise NaoEncontradoError("Unidade consumidora não encontrada.")
        return uc


class LoteService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = LoteRepository(db)
        self.uc_repo = UnidadeConsumidoraRepository(db)
        self.acesso_repo = AcessoClienteRepository(db)

    def criar(self, dados: LoteCreate, ator: UsuarioAutenticado) -> LoteOut:
        uc = self.uc_repo.buscar_por_id(dados.unidade_consumidora_id)
        if uc is None:
            raise NaoEncontradoError("Unidade consumidora não encontrada.")
        if PapelUsuario(ator.papel) != PapelUsuario.ADMIN:
            acesso = self.acesso_repo.buscar(usuario_id=ator.id, cliente_id=uc.cliente_id)
            if acesso is None:
                raise AcessoNegadoError("Acesso não autorizado.")
        lote = self.repo.criar(dados, criado_por_id=ator.id)
        self.db.commit()
        self.db.refresh(lote)
        return LoteOut.model_validate(lote)

    def listar(
        self, pag: PaginacaoKeyset, ator: UsuarioAutenticado, uc_id: uuid.UUID | None = None
    ) -> PageKeysetOut[LoteResumoOut]:
        is_admin = PapelUsuario(ator.papel) == PapelUsuario.ADMIN
        lotes = self.repo.listar(
            pag=pag,
            uc_id=uc_id,
            usuario_id=ator.id,
            apenas_acessiveis=not is_admin,
        )
        has_more = len(lotes) > pag.limite
        page = lotes[: pag.limite]
        next_cursor = page[-1].id if has_more and page else None
        return PageKeysetOut(
            data=[LoteResumoOut.model_validate(l) for l in page],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def obter(self, id: uuid.UUID, ator: UsuarioAutenticado) -> LoteOut:
        lote = self._obter_orm(id)
        if PapelUsuario(ator.papel) != PapelUsuario.ADMIN:
            uc = self.uc_repo.buscar_por_id(lote.unidade_consumidora_id)
            if uc is None:
                raise NaoEncontradoError("Lote não encontrado.")
            acesso = self.acesso_repo.buscar(usuario_id=ator.id, cliente_id=uc.cliente_id)
            if acesso is None:
                raise AcessoNegadoError("Acesso não autorizado.")
        return LoteOut.model_validate(lote)

    def atualizar(
        self, id: uuid.UUID, dados: LoteUpdate, ator: UsuarioAutenticado
    ) -> LoteOut:
        lote = self._obter_orm(id)
        is_admin = PapelUsuario(ator.papel) == PapelUsuario.ADMIN
        if not is_admin:
            uc = self.uc_repo.buscar_por_id(lote.unidade_consumidora_id)
            if uc is None:
                raise NaoEncontradoError("Lote não encontrado.")
            acesso = self.acesso_repo.buscar(usuario_id=ator.id, cliente_id=uc.cliente_id)
            if acesso is None or not acesso.pode_editar:
                raise AcessoNegadoError("Você não tem permissão para editar este lote.")
        if dados.status is not None and not is_admin:
            raise RegraVioladaError("Apenas administradores podem alterar o status do lote.")
        self.repo.atualizar(lote, dados, pode_alterar_status=is_admin)
        self.db.commit()
        self.db.refresh(lote)
        return LoteOut.model_validate(lote)

    def deletar(self, id: uuid.UUID, ator: UsuarioAutenticado, permanente: bool = False) -> None:
        lote = self._obter_orm(id)
        if PapelUsuario(ator.papel) != PapelUsuario.ADMIN:
            uc = self.uc_repo.buscar_por_id(lote.unidade_consumidora_id)
            if uc is None:
                raise NaoEncontradoError("Lote não encontrado.")
            acesso = self.acesso_repo.buscar(usuario_id=ator.id, cliente_id=uc.cliente_id)
            if acesso is None or not acesso.pode_editar:
                raise AcessoNegadoError("Você não tem permissão para excluir este lote.")
        if permanente and PapelUsuario(ator.papel) != PapelUsuario.ADMIN:
            raise AcessoNegadoError("Apenas administradores podem excluir permanentemente.")
        if permanente:
            self.repo.remover(lote)
        else:
            self.repo.desativar(lote)
        self.db.commit()

    def _obter_orm(self, id: uuid.UUID) -> LoteAuditoria:
        lote = self.repo.buscar_por_id(id)
        if lote is None:
            raise NaoEncontradoError("Lote não encontrado.")
        return lote
