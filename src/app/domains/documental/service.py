import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app.core.enums import PapelUsuario, StatusExtracao
from src.app.core.exceptions import (
    AcessoNegadoError,
    ConflitoDuplicidadeError,
    NaoEncontradoError,
    RegraVioladaError,
)
from src.app.domains.auth.service import UsuarioAutenticado
from src.app.domains.clientes.models import AcessoCliente, LoteAuditoria, UnidadeConsumidora
from src.app.domains.clientes.repository import (
    AcessoClienteRepository,
    DistribuidoraRepository,
    LoteRepository,
    UnidadeConsumidoraRepository,
)
from src.app.domains.documental.models import DocumentoBruto, LayoutFatura
from src.app.domains.documental.repository import DocumentoBrutoRepository, LayoutFaturaRepository
from src.app.domains.documental.schemas import (
    DocumentoBrutoCreate,
    DocumentoBrutoOut,
    DocumentoBrutoResumoOut,
    DocumentoBrutoUpdate,
    DocumentosBrutosOut,
    LayoutFaturaCreate,
    LayoutFaturaOut,
    LayoutFaturaUpdate,
)


class LayoutFaturaService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = LayoutFaturaRepository(db)
        self.dist_repo = DistribuidoraRepository(db)

    def criar(self, dados: LayoutFaturaCreate, ator: UsuarioAutenticado) -> LayoutFaturaOut:
        self._exigir_admin(ator, "Apenas administradores podem cadastrar layouts de fatura.")
        if self.dist_repo.buscar_por_id(dados.distribuidora_id) is None:
            raise NaoEncontradoError("Distribuidora não encontrada.")
        try:
            layout = self.repo.criar(dados)
            self.db.commit()
            self.db.refresh(layout)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflitoDuplicidadeError("Já existe um layout com este código.") from exc
        return LayoutFaturaOut.model_validate(layout)

    def listar(self, distribuidora_id: uuid.UUID | None = None) -> list[LayoutFaturaOut]:
        return [
            LayoutFaturaOut.model_validate(layout)
            for layout in self.repo.listar(distribuidora_id)
        ]

    def obter(self, id: uuid.UUID) -> LayoutFaturaOut:
        return LayoutFaturaOut.model_validate(self._obter_orm(id))

    def atualizar(
        self, id: uuid.UUID, dados: LayoutFaturaUpdate, ator: UsuarioAutenticado
    ) -> LayoutFaturaOut:
        self._exigir_admin(ator, "Apenas administradores podem editar layouts de fatura.")
        layout = self._obter_orm(id)
        if dados.distribuidora_id is not None and self.dist_repo.buscar_por_id(
            dados.distribuidora_id
        ) is None:
            raise NaoEncontradoError("Distribuidora não encontrada.")
        inicio = dados.vigencia_inicio or layout.vigencia_inicio
        fim = (
            dados.vigencia_fim
            if "vigencia_fim" in dados.model_fields_set
            else layout.vigencia_fim
        )
        if fim is not None and fim < inicio:
            raise RegraVioladaError("vigencia_fim deve ser igual ou posterior a vigencia_inicio.")
        try:
            self.repo.atualizar(layout, dados)
            self.db.commit()
            self.db.refresh(layout)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflitoDuplicidadeError("Já existe um layout com este código.") from exc
        return LayoutFaturaOut.model_validate(layout)

    def deletar(self, id: uuid.UUID, ator: UsuarioAutenticado, permanente: bool = False) -> None:
        self._exigir_admin(ator, "Apenas administradores podem excluir layouts de fatura.")
        layout = self._obter_orm(id)
        if permanente:
            self.repo.remover(layout)
        else:
            self.repo.desativar(layout)
        self.db.commit()

    def _obter_orm(self, id: uuid.UUID) -> LayoutFatura:
        layout = self.repo.buscar_por_id(id)
        if layout is None:
            raise NaoEncontradoError("Layout de fatura não encontrado.")
        return layout

    @staticmethod
    def _exigir_admin(ator: UsuarioAutenticado, mensagem: str) -> None:
        if PapelUsuario(ator.papel) != PapelUsuario.ADMIN:
            raise AcessoNegadoError(mensagem)


class DocumentoBrutoService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DocumentoBrutoRepository(db)
        self.uc_repo = UnidadeConsumidoraRepository(db)
        self.lote_repo = LoteRepository(db)
        self.acesso_repo = AcessoClienteRepository(db)
        self.layout_repo = LayoutFaturaRepository(db)

    def criar(self, dados: DocumentoBrutoCreate, ator: UsuarioAutenticado) -> DocumentoBrutoOut:
        uc = self._obter_uc(dados.unidade_consumidora_id)
        self._verificar_acesso_uc(uc, ator, exigir_edicao=True)
        self._validar_lote(dados.lote_auditoria_id, uc.id)
        self._validar_layout(dados.layout_fatura_id, uc.distribuidora_id)
        try:
            documento = self.repo.criar(dados, enviado_por_id=ator.id)
            self.db.commit()
            self.db.refresh(documento)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflitoDuplicidadeError("Já existe um documento com este sha256.") from exc
        return DocumentoBrutoOut.model_validate(documento)

    def listar(
        self,
        ator: UsuarioAutenticado,
        unidade_consumidora_id: uuid.UUID | None = None,
        lote_auditoria_id: uuid.UUID | None = None,
        status_extracao: StatusExtracao | None = None,
    ) -> DocumentosBrutosOut:
        is_admin = PapelUsuario(ator.papel) == PapelUsuario.ADMIN
        documentos = self.repo.listar(
            usuario_id=ator.id,
            apenas_acessiveis=not is_admin,
            unidade_consumidora_id=unidade_consumidora_id,
            lote_auditoria_id=lote_auditoria_id,
            status_extracao=status_extracao,
        )
        return DocumentosBrutosOut(
            itens=[DocumentoBrutoResumoOut.model_validate(d) for d in documentos],
            total=len(documentos),
        )

    def obter(self, id: uuid.UUID, ator: UsuarioAutenticado) -> DocumentoBrutoOut:
        documento = self._obter_orm(id)
        uc = self._obter_uc(documento.unidade_consumidora_id)
        self._verificar_acesso_uc(uc, ator, exigir_edicao=False)
        return DocumentoBrutoOut.model_validate(documento)

    def atualizar(
        self, id: uuid.UUID, dados: DocumentoBrutoUpdate, ator: UsuarioAutenticado
    ) -> DocumentoBrutoOut:
        documento = self._obter_orm(id)
        uc = self._obter_uc(documento.unidade_consumidora_id)
        self._verificar_acesso_uc(uc, ator, exigir_edicao=True)
        self._validar_lote(dados.lote_auditoria_id, uc.id)
        self._validar_layout(dados.layout_fatura_id, uc.distribuidora_id)
        self.repo.atualizar(documento, dados)
        self.db.commit()
        self.db.refresh(documento)
        return DocumentoBrutoOut.model_validate(documento)

    def deletar(self, id: uuid.UUID, ator: UsuarioAutenticado) -> None:
        documento = self._obter_orm(id)
        uc = self._obter_uc(documento.unidade_consumidora_id)
        self._verificar_acesso_uc(uc, ator, exigir_edicao=True)
        self.repo.remover(documento)
        self.db.commit()

    def _obter_orm(self, id: uuid.UUID) -> DocumentoBruto:
        documento = self.repo.buscar_por_id(id)
        if documento is None:
            raise NaoEncontradoError("Documento bruto não encontrado.")
        return documento

    def _obter_uc(self, id: uuid.UUID) -> UnidadeConsumidora:
        uc = self.uc_repo.buscar_por_id(id)
        if uc is None:
            raise NaoEncontradoError("Unidade consumidora não encontrada.")
        return uc

    def _validar_lote(self, lote_id: uuid.UUID | None, uc_id: uuid.UUID) -> LoteAuditoria | None:
        if lote_id is None:
            return None
        lote = self.lote_repo.buscar_por_id(lote_id)
        if lote is None or lote.unidade_consumidora_id != uc_id:
            raise RegraVioladaError("Lote de auditoria não pertence à unidade consumidora.")
        return lote

    def _validar_layout(
        self, layout_id: uuid.UUID | None, distribuidora_id: uuid.UUID
    ) -> LayoutFatura | None:
        if layout_id is None:
            return None
        layout = self.layout_repo.buscar_por_id(layout_id)
        if layout is None:
            raise NaoEncontradoError("Layout de fatura não encontrado.")
        if layout.distribuidora_id != distribuidora_id:
            raise RegraVioladaError("Layout de fatura não pertence à distribuidora da UC.")
        return layout

    def _verificar_acesso_uc(
        self,
        uc: UnidadeConsumidora,
        ator: UsuarioAutenticado,
        exigir_edicao: bool,
    ) -> AcessoCliente | None:
        if PapelUsuario(ator.papel) == PapelUsuario.ADMIN:
            return None
        acesso = self.acesso_repo.buscar(usuario_id=ator.id, cliente_id=uc.cliente_id)
        if acesso is None:
            raise AcessoNegadoError("Acesso não autorizado.")
        if exigir_edicao and not acesso.pode_editar:
            raise AcessoNegadoError("Você não tem permissão para alterar documentos desta UC.")
        return acesso
