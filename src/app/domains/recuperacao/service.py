import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app.core.enums import PapelUsuario, StatusAchado, StatusRecuperacao
from src.app.core.exceptions import (
    AcessoNegadoError,
    ConflitoDuplicidadeError,
    NaoEncontradoError,
    RegraVioladaError,
)
from src.app.domains.auditoria.models import Achado
from src.app.domains.auditoria.repository import AchadoRepository
from src.app.domains.auth.models import Usuario
from src.app.domains.auth.service import UsuarioAutenticado
from src.app.domains.clientes.models import (
    AcessoCliente,
    Cliente,
    LoteAuditoria,
    UnidadeConsumidora,
)
from src.app.domains.clientes.repository import (
    AcessoClienteRepository,
    ClienteRepository,
    LoteRepository,
    UnidadeConsumidoraRepository,
)
from src.app.domains.faturas.models import Fatura
from src.app.domains.faturas.repository import FaturaRepository
from src.app.domains.recuperacao.models import CasoRecuperacao, ItemRecuperacao
from src.app.domains.recuperacao.repository import (
    CasoRecuperacaoRepository,
    ItemRecuperacaoRepository,
)
from src.app.domains.recuperacao.schemas import (
    CasoRecuperacaoCreate,
    CasoRecuperacaoDetalheOut,
    CasoRecuperacaoOut,
    CasoRecuperacaoUpdate,
    CasosRecuperacaoOut,
    ItemRecuperacaoCreate,
    ItemRecuperacaoOut,
    ItemRecuperacaoUpdate,
)


class RecuperacaoService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.caso_repo = CasoRecuperacaoRepository(db)
        self.item_repo = ItemRecuperacaoRepository(db)
        self.cliente_repo = ClienteRepository(db)
        self.uc_repo = UnidadeConsumidoraRepository(db)
        self.lote_repo = LoteRepository(db)
        self.acesso_repo = AcessoClienteRepository(db)
        self.achado_repo = AchadoRepository(db)
        self.fatura_repo = FaturaRepository(db)

    def criar(
        self, dados: CasoRecuperacaoCreate, ator: UsuarioAutenticado
    ) -> CasoRecuperacaoDetalheOut:
        cliente, uc = self._validar_contexto(dados.cliente_id, dados.unidade_consumidora_id)
        self._verificar_acesso_cliente(cliente.id, ator, exigir_edicao=True)
        self._validar_lote(dados.lote_auditoria_id, uc.id)
        self._validar_usuario(dados.responsavel_id)
        numero = dados.numero_caso or self._gerar_numero_caso()
        try:
            caso = self.caso_repo.criar(dados, criado_por_id=ator.id, numero_caso=numero)
            self.caso_repo.recalcular_totais(caso)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflitoDuplicidadeError("Já existe um caso com este número.") from exc
        return self.obter(caso.id, ator=ator)

    def listar(
        self,
        ator: UsuarioAutenticado,
        cliente_id: uuid.UUID | None = None,
        unidade_consumidora_id: uuid.UUID | None = None,
        status: StatusRecuperacao | None = None,
    ) -> CasosRecuperacaoOut:
        if cliente_id is not None:
            self._obter_cliente(cliente_id)
            self._verificar_acesso_cliente(cliente_id, ator, exigir_edicao=False)
        casos = self.caso_repo.listar(
            cliente_id=cliente_id,
            unidade_consumidora_id=unidade_consumidora_id,
            status=status,
        )
        if PapelUsuario(ator.papel) != PapelUsuario.ADMIN and cliente_id is None:
            casos = [caso for caso in casos if self._ator_acessa_cliente(caso.cliente_id, ator)]
        return CasosRecuperacaoOut(
            itens=[CasoRecuperacaoOut.model_validate(c) for c in casos],
            total=len(casos),
        )

    def obter(self, id: uuid.UUID, ator: UsuarioAutenticado) -> CasoRecuperacaoDetalheOut:
        caso = self._obter_caso(id, detalhe=True)
        self._verificar_acesso_cliente(caso.cliente_id, ator, exigir_edicao=False)
        return CasoRecuperacaoDetalheOut.model_validate(caso)

    def atualizar(
        self, id: uuid.UUID, dados: CasoRecuperacaoUpdate, ator: UsuarioAutenticado
    ) -> CasoRecuperacaoDetalheOut:
        caso = self._obter_caso(id)
        self._verificar_acesso_cliente(caso.cliente_id, ator, exigir_edicao=True)
        self._validar_usuario(dados.responsavel_id)
        try:
            self.caso_repo.atualizar(caso, dados)
            if dados.status == StatusRecuperacao.CONCLUIDO and dados.fechado_em is None:
                caso.fechado_em = datetime.now(UTC)
            self.caso_repo.recalcular_totais(caso)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflitoDuplicidadeError("Já existe um caso com este número.") from exc
        return self.obter(caso.id, ator=ator)

    def deletar(self, id: uuid.UUID, ator: UsuarioAutenticado) -> None:
        caso = self._obter_caso(id)
        self._verificar_acesso_cliente(caso.cliente_id, ator, exigir_edicao=True)
        self.caso_repo.remover(caso)
        self.db.commit()

    def listar_itens(
        self, caso_id: uuid.UUID, ator: UsuarioAutenticado
    ) -> list[ItemRecuperacaoOut]:
        caso = self._obter_caso(caso_id)
        self._verificar_acesso_cliente(caso.cliente_id, ator, exigir_edicao=False)
        return [
            ItemRecuperacaoOut.model_validate(i)
            for i in self.item_repo.listar_por_caso(caso_id)
        ]

    def criar_item(
        self, caso_id: uuid.UUID, dados: ItemRecuperacaoCreate, ator: UsuarioAutenticado
    ) -> ItemRecuperacaoOut:
        caso = self._obter_caso(caso_id)
        self._verificar_acesso_cliente(caso.cliente_id, ator, exigir_edicao=True)
        self._validar_item_contexto(caso, dados.achado_id, dados.fatura_id)
        item = self.item_repo.criar(caso.id, dados)
        self.caso_repo.recalcular_totais(caso)
        self.db.commit()
        self.db.refresh(item)
        return ItemRecuperacaoOut.model_validate(item)

    def atualizar_item(
        self,
        caso_id: uuid.UUID,
        item_id: uuid.UUID,
        dados: ItemRecuperacaoUpdate,
        ator: UsuarioAutenticado,
    ) -> ItemRecuperacaoOut:
        caso = self._obter_caso(caso_id)
        self._verificar_acesso_cliente(caso.cliente_id, ator, exigir_edicao=True)
        item = self._obter_item(item_id, caso_id)
        self.item_repo.atualizar(item, dados)
        self.caso_repo.recalcular_totais(caso)
        self.db.commit()
        self.db.refresh(item)
        return ItemRecuperacaoOut.model_validate(item)

    def deletar_item(
        self, caso_id: uuid.UUID, item_id: uuid.UUID, ator: UsuarioAutenticado
    ) -> None:
        caso = self._obter_caso(caso_id)
        self._verificar_acesso_cliente(caso.cliente_id, ator, exigir_edicao=True)
        item = self._obter_item(item_id, caso_id)
        self.item_repo.remover(item)
        self.caso_repo.recalcular_totais(caso)
        self.db.commit()

    def _validar_contexto(
        self, cliente_id: uuid.UUID, unidade_consumidora_id: uuid.UUID
    ) -> tuple[Cliente, UnidadeConsumidora]:
        cliente = self._obter_cliente(cliente_id)
        uc = self._obter_uc(unidade_consumidora_id)
        if uc.cliente_id != cliente.id:
            raise RegraVioladaError("Unidade consumidora não pertence ao cliente.")
        return cliente, uc

    def _validar_lote(self, lote_id: uuid.UUID | None, uc_id: uuid.UUID) -> LoteAuditoria | None:
        if lote_id is None:
            return None
        lote = self.lote_repo.buscar_por_id(lote_id)
        if lote is None or lote.unidade_consumidora_id != uc_id:
            raise RegraVioladaError("Lote de auditoria não pertence à UC do caso.")
        return lote

    def _validar_usuario(self, usuario_id: uuid.UUID | None) -> None:
        if usuario_id is not None and self.db.get(Usuario, usuario_id) is None:
            raise NaoEncontradoError("Usuário responsável não encontrado.")

    def _validar_item_contexto(
        self, caso: CasoRecuperacao, achado_id: uuid.UUID, fatura_id: uuid.UUID
    ) -> None:
        achado = self._obter_achado(achado_id)
        if achado.status != StatusAchado.CONFIRMADO:
            raise RegraVioladaError("Item de recuperação exige achado confirmado.")
        if achado.fatura_id != fatura_id:
            raise RegraVioladaError("Achado não pertence à fatura informada.")
        fatura = self._obter_fatura(fatura_id)
        uc = self._obter_uc(fatura.unidade_consumidora_id)
        if uc.id != caso.unidade_consumidora_id or uc.cliente_id != caso.cliente_id:
            raise RegraVioladaError("Item de recuperação não pertence ao contexto do caso.")

    def _obter_cliente(self, cliente_id: uuid.UUID) -> Cliente:
        cliente = self.cliente_repo.buscar_por_id(cliente_id)
        if cliente is None:
            raise NaoEncontradoError("Cliente não encontrado.")
        return cliente

    def _obter_uc(self, uc_id: uuid.UUID) -> UnidadeConsumidora:
        uc = self.uc_repo.buscar_por_id(uc_id)
        if uc is None:
            raise NaoEncontradoError("Unidade consumidora não encontrada.")
        return uc

    def _obter_fatura(self, fatura_id: uuid.UUID) -> Fatura:
        fatura = self.fatura_repo.buscar_por_id(fatura_id)
        if fatura is None:
            raise NaoEncontradoError("Fatura não encontrada.")
        return fatura

    def _obter_achado(self, achado_id: uuid.UUID) -> Achado:
        achado = self.achado_repo.buscar_por_id(achado_id)
        if achado is None:
            raise NaoEncontradoError("Achado não encontrado.")
        return achado

    def _obter_caso(self, caso_id: uuid.UUID, detalhe: bool = False) -> CasoRecuperacao:
        caso = self.caso_repo.buscar_por_id(caso_id, detalhe=detalhe)
        if caso is None:
            raise NaoEncontradoError("Caso de recuperação não encontrado.")
        return caso

    def _obter_item(self, item_id: uuid.UUID, caso_id: uuid.UUID) -> ItemRecuperacao:
        item = self.item_repo.buscar_por_id(item_id)
        if item is None or item.caso_recuperacao_id != caso_id:
            raise NaoEncontradoError("Item de recuperação não encontrado.")
        return item

    def _verificar_acesso_cliente(
        self, cliente_id: uuid.UUID, ator: UsuarioAutenticado, exigir_edicao: bool
    ) -> AcessoCliente | None:
        if PapelUsuario(ator.papel) == PapelUsuario.ADMIN:
            return None
        acesso = self.acesso_repo.buscar(usuario_id=ator.id, cliente_id=cliente_id)
        if acesso is None:
            raise AcessoNegadoError("Acesso não autorizado.")
        if exigir_edicao and not acesso.pode_editar:
            raise AcessoNegadoError("Você não tem permissão para alterar recuperação.")
        return acesso

    def _ator_acessa_cliente(self, cliente_id: uuid.UUID, ator: UsuarioAutenticado) -> bool:
        try:
            self._verificar_acesso_cliente(cliente_id, ator, exigir_edicao=False)
        except AcessoNegadoError:
            return False
        return True

    @staticmethod
    def _gerar_numero_caso() -> str:
        agora = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return f"CASO-{agora}-{uuid.uuid4().hex[:8].upper()}"
