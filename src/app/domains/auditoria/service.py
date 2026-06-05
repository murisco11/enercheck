import uuid

from sqlalchemy.orm import Session

from src.app.core.enums import PapelUsuario, StatusAchado
from src.app.core.exceptions import AcessoNegadoError, NaoEncontradoError
from src.app.domains.auditoria.models import Achado
from src.app.domains.auditoria.repository import AchadoRepository, ExecucaoValidacaoRepository
from src.app.domains.auditoria.schemas import (
    AchadoCreate,
    AchadoOut,
    AchadosOut,
    AchadoUpdate,
    ExecucaoValidacaoDetalheOut,
    ExecucaoValidacaoOut,
)
from src.app.domains.auth.service import UsuarioAutenticado
from src.app.domains.clientes.models import AcessoCliente, UnidadeConsumidora
from src.app.domains.clientes.repository import (
    AcessoClienteRepository,
    UnidadeConsumidoraRepository,
)
from src.app.domains.faturas.models import Fatura
from src.app.domains.faturas.repository import FaturaRepository


class ValidacaoService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.exec_repo = ExecucaoValidacaoRepository(db)
        self.fatura_repo = FaturaRepository(db)
        self.uc_repo = UnidadeConsumidoraRepository(db)
        self.acesso_repo = AcessoClienteRepository(db)

    def listar_por_fatura(
        self, fatura_id: uuid.UUID, ator: UsuarioAutenticado
    ) -> list[ExecucaoValidacaoOut]:
        fatura = self._obter_fatura(fatura_id)
        uc = self._obter_uc(fatura.unidade_consumidora_id)
        self._verificar_acesso_uc(uc, ator, exigir_edicao=False)
        return [
            ExecucaoValidacaoOut.model_validate(e)
            for e in self.exec_repo.listar_por_fatura(fatura_id)
        ]

    def obter(self, id: uuid.UUID, ator: UsuarioAutenticado) -> ExecucaoValidacaoDetalheOut:
        execucao = self.exec_repo.buscar_por_id(id, detalhe=True)
        if execucao is None:
            raise NaoEncontradoError("Execução de validação não encontrada.")
        fatura = self._obter_fatura(execucao.fatura_id)
        uc = self._obter_uc(fatura.unidade_consumidora_id)
        self._verificar_acesso_uc(uc, ator, exigir_edicao=False)
        return ExecucaoValidacaoDetalheOut.model_validate(execucao)

    def _obter_fatura(self, fatura_id: uuid.UUID) -> Fatura:
        fatura = self.fatura_repo.buscar_por_id(fatura_id)
        if fatura is None:
            raise NaoEncontradoError("Fatura não encontrada.")
        return fatura

    def _obter_uc(self, uc_id: uuid.UUID) -> UnidadeConsumidora:
        uc = self.uc_repo.buscar_por_id(uc_id)
        if uc is None:
            raise NaoEncontradoError("Unidade consumidora não encontrada.")
        return uc

    def _verificar_acesso_uc(
        self, uc: UnidadeConsumidora, ator: UsuarioAutenticado, exigir_edicao: bool
    ) -> AcessoCliente | None:
        if PapelUsuario(ator.papel) == PapelUsuario.ADMIN:
            return None
        acesso = self.acesso_repo.buscar(usuario_id=ator.id, cliente_id=uc.cliente_id)
        if acesso is None:
            raise AcessoNegadoError("Acesso não autorizado.")
        if exigir_edicao and not acesso.pode_editar:
            raise AcessoNegadoError("Você não tem permissão para validar faturas desta UC.")
        return acesso


class AchadoService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AchadoRepository(db)
        self.fatura_repo = FaturaRepository(db)
        self.uc_repo = UnidadeConsumidoraRepository(db)
        self.acesso_repo = AcessoClienteRepository(db)

    def criar(self, dados: AchadoCreate, ator: UsuarioAutenticado) -> AchadoOut:
        fatura = self._obter_fatura(dados.fatura_id)
        uc = self._obter_uc(fatura.unidade_consumidora_id)
        self._verificar_acesso_uc(uc, ator, exigir_edicao=True)
        achado = self.repo.criar(dados)
        self.db.commit()
        self.db.refresh(achado)
        return AchadoOut.model_validate(achado)

    def listar(
        self,
        ator: UsuarioAutenticado,
        fatura_id: uuid.UUID | None = None,
        status: StatusAchado | None = None,
    ) -> AchadosOut:
        if fatura_id is not None:
            fatura = self._obter_fatura(fatura_id)
            uc = self._obter_uc(fatura.unidade_consumidora_id)
            self._verificar_acesso_uc(uc, ator, exigir_edicao=False)
        achados = self.repo.listar(fatura_id=fatura_id, status=status)
        if PapelUsuario(ator.papel) != PapelUsuario.ADMIN and fatura_id is None:
            achados = [a for a in achados if self._ator_acessa_achado(a, ator)]
        return AchadosOut(itens=[AchadoOut.model_validate(a) for a in achados], total=len(achados))

    def obter(self, id: uuid.UUID, ator: UsuarioAutenticado) -> AchadoOut:
        achado = self._obter_orm(id)
        self._verificar_acesso_achado(achado, ator, exigir_edicao=False)
        return AchadoOut.model_validate(achado)

    def atualizar(
        self, id: uuid.UUID, dados: AchadoUpdate, ator: UsuarioAutenticado
    ) -> AchadoOut:
        achado = self._obter_orm(id)
        self._verificar_acesso_achado(achado, ator, exigir_edicao=True)
        self.repo.atualizar(achado, dados)
        self.db.commit()
        self.db.refresh(achado)
        return AchadoOut.model_validate(achado)

    def deletar(self, id: uuid.UUID, ator: UsuarioAutenticado) -> None:
        achado = self._obter_orm(id)
        self._verificar_acesso_achado(achado, ator, exigir_edicao=True)
        self.repo.remover(achado)
        self.db.commit()

    def _obter_orm(self, id: uuid.UUID) -> Achado:
        achado = self.repo.buscar_por_id(id)
        if achado is None:
            raise NaoEncontradoError("Achado não encontrado.")
        return achado

    def _obter_fatura(self, fatura_id: uuid.UUID) -> Fatura:
        fatura = self.fatura_repo.buscar_por_id(fatura_id)
        if fatura is None:
            raise NaoEncontradoError("Fatura não encontrada.")
        return fatura

    def _obter_uc(self, uc_id: uuid.UUID) -> UnidadeConsumidora:
        uc = self.uc_repo.buscar_por_id(uc_id)
        if uc is None:
            raise NaoEncontradoError("Unidade consumidora não encontrada.")
        return uc

    def _verificar_acesso_achado(
        self, achado: Achado, ator: UsuarioAutenticado, exigir_edicao: bool
    ) -> None:
        fatura = self._obter_fatura(achado.fatura_id)
        uc = self._obter_uc(fatura.unidade_consumidora_id)
        self._verificar_acesso_uc(uc, ator, exigir_edicao=exigir_edicao)

    def _ator_acessa_achado(self, achado: Achado, ator: UsuarioAutenticado) -> bool:
        try:
            self._verificar_acesso_achado(achado, ator, exigir_edicao=False)
        except AcessoNegadoError:
            return False
        return True

    def _verificar_acesso_uc(
        self, uc: UnidadeConsumidora, ator: UsuarioAutenticado, exigir_edicao: bool
    ) -> AcessoCliente | None:
        if PapelUsuario(ator.papel) == PapelUsuario.ADMIN:
            return None
        acesso = self.acesso_repo.buscar(usuario_id=ator.id, cliente_id=uc.cliente_id)
        if acesso is None:
            raise AcessoNegadoError("Acesso não autorizado.")
        if exigir_edicao and not acesso.pode_editar:
            raise AcessoNegadoError("Você não tem permissão para alterar achados desta UC.")
        return acesso
