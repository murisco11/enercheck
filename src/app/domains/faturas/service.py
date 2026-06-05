import uuid
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app.core.enums import PapelUsuario
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
    LoteRepository,
    UnidadeConsumidoraRepository,
)
from src.app.domains.documental.models import DocumentoBruto
from src.app.domains.faturas.models import Fatura, ItemFatura, MedidaFatura, TributoFatura
from src.app.domains.faturas.repository import (
    FaturaRepository,
    ItemFaturaRepository,
    MedidaFaturaRepository,
    TributoFaturaRepository,
)
from src.app.domains.faturas.schemas import (
    FaturaCreate,
    FaturaDetalheOut,
    FaturaOut,
    FaturaResumoOut,
    FaturasOut,
    FaturaUpdate,
    ItemFaturaCreate,
    ItemFaturaOut,
    ItemFaturaUpdate,
    MedidaFaturaCreate,
    MedidaFaturaOut,
    MedidaFaturaUpdate,
    TributoFaturaCreate,
    TributoFaturaOut,
    TributoFaturaUpdate,
)

TOLERANCIA_TOTAL = Decimal("0.01")


class FaturaService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = FaturaRepository(db)
        self.uc_repo = UnidadeConsumidoraRepository(db)
        self.lote_repo = LoteRepository(db)
        self.acesso_repo = AcessoClienteRepository(db)
        self.medida_repo = MedidaFaturaRepository(db)
        self.item_repo = ItemFaturaRepository(db)
        self.tributo_repo = TributoFaturaRepository(db)

    def criar(self, dados: FaturaCreate, ator: UsuarioAutenticado) -> FaturaDetalheOut:
        uc = self._obter_uc(dados.unidade_consumidora_id)
        self._verificar_acesso_uc(uc, ator, exigir_edicao=True)
        self._validar_lote(dados.lote_auditoria_id, uc.id)
        self._validar_documento(dados.documento_bruto_id, uc.id)
        self._validar_total(dados)
        try:
            fatura = self.repo.criar(dados)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflitoDuplicidadeError(
                "Já existe uma fatura com esta chave de acesso ou tributo duplicado."
            ) from exc
        return self.obter(fatura.id, ator=ator)

    def listar(
        self,
        ator: UsuarioAutenticado,
        unidade_consumidora_id: uuid.UUID | None = None,
        lote_auditoria_id: uuid.UUID | None = None,
        competencia: str | None = None,
    ) -> FaturasOut:
        is_admin = PapelUsuario(ator.papel) == PapelUsuario.ADMIN
        faturas = self.repo.listar(
            usuario_id=ator.id,
            apenas_acessiveis=not is_admin,
            unidade_consumidora_id=unidade_consumidora_id,
            lote_auditoria_id=lote_auditoria_id,
            competencia=competencia,
        )
        return FaturasOut(
            itens=[FaturaResumoOut.model_validate(f) for f in faturas],
            total=len(faturas),
        )

    def obter(self, id: uuid.UUID, ator: UsuarioAutenticado) -> FaturaDetalheOut:
        fatura = self._obter_orm(id, detalhe=True)
        uc = self._obter_uc(fatura.unidade_consumidora_id)
        self._verificar_acesso_uc(uc, ator, exigir_edicao=False)
        return FaturaDetalheOut.model_validate(fatura)

    def atualizar(
        self, id: uuid.UUID, dados: FaturaUpdate, ator: UsuarioAutenticado
    ) -> FaturaOut:
        fatura = self._obter_orm(id)
        uc = self._obter_uc(fatura.unidade_consumidora_id)
        self._verificar_acesso_uc(uc, ator, exigir_edicao=True)
        self._validar_lote(dados.lote_auditoria_id, uc.id)
        self._validar_documento(dados.documento_bruto_id, uc.id)
        try:
            self.repo.atualizar(fatura, dados)
            self.db.commit()
            self.db.refresh(fatura)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflitoDuplicidadeError(
                "Já existe uma fatura com esta chave de acesso."
            ) from exc
        return FaturaOut.model_validate(fatura)

    def deletar(self, id: uuid.UUID, ator: UsuarioAutenticado) -> None:
        fatura = self._obter_orm(id)
        uc = self._obter_uc(fatura.unidade_consumidora_id)
        self._verificar_acesso_uc(uc, ator, exigir_edicao=True)
        self.repo.remover(fatura)
        self.db.commit()

    def listar_medidas(
        self, fatura_id: uuid.UUID, ator: UsuarioAutenticado
    ) -> list[MedidaFaturaOut]:
        self._verificar_acesso_fatura(fatura_id, ator, exigir_edicao=False)
        return [MedidaFaturaOut.model_validate(m) for m in self.medida_repo.listar(fatura_id)]

    def criar_medida(
        self, fatura_id: uuid.UUID, dados: MedidaFaturaCreate, ator: UsuarioAutenticado
    ) -> MedidaFaturaOut:
        self._verificar_acesso_fatura(fatura_id, ator, exigir_edicao=True)
        medida = self.medida_repo.criar(fatura_id, dados)
        self.db.commit()
        self.db.refresh(medida)
        return MedidaFaturaOut.model_validate(medida)

    def atualizar_medida(
        self,
        fatura_id: uuid.UUID,
        medida_id: uuid.UUID,
        dados: MedidaFaturaUpdate,
        ator: UsuarioAutenticado,
    ) -> MedidaFaturaOut:
        self._verificar_acesso_fatura(fatura_id, ator, exigir_edicao=True)
        medida = self._obter_medida(medida_id, fatura_id)
        self.medida_repo.atualizar(medida, dados)
        self.db.commit()
        self.db.refresh(medida)
        return MedidaFaturaOut.model_validate(medida)

    def deletar_medida(
        self, fatura_id: uuid.UUID, medida_id: uuid.UUID, ator: UsuarioAutenticado
    ) -> None:
        self._verificar_acesso_fatura(fatura_id, ator, exigir_edicao=True)
        medida = self._obter_medida(medida_id, fatura_id)
        self.medida_repo.remover(medida)
        self.db.commit()

    def listar_itens(self, fatura_id: uuid.UUID, ator: UsuarioAutenticado) -> list[ItemFaturaOut]:
        self._verificar_acesso_fatura(fatura_id, ator, exigir_edicao=False)
        return [ItemFaturaOut.model_validate(i) for i in self.item_repo.listar(fatura_id)]

    def criar_item(
        self, fatura_id: uuid.UUID, dados: ItemFaturaCreate, ator: UsuarioAutenticado
    ) -> ItemFaturaOut:
        self._verificar_acesso_fatura(fatura_id, ator, exigir_edicao=True)
        item = self.item_repo.criar(fatura_id, dados)
        self.db.commit()
        self.db.refresh(item)
        return ItemFaturaOut.model_validate(item)

    def atualizar_item(
        self,
        fatura_id: uuid.UUID,
        item_id: uuid.UUID,
        dados: ItemFaturaUpdate,
        ator: UsuarioAutenticado,
    ) -> ItemFaturaOut:
        self._verificar_acesso_fatura(fatura_id, ator, exigir_edicao=True)
        item = self._obter_item(item_id, fatura_id)
        self.item_repo.atualizar(item, dados)
        self.db.commit()
        self.db.refresh(item)
        return ItemFaturaOut.model_validate(item)

    def deletar_item(
        self, fatura_id: uuid.UUID, item_id: uuid.UUID, ator: UsuarioAutenticado
    ) -> None:
        self._verificar_acesso_fatura(fatura_id, ator, exigir_edicao=True)
        item = self._obter_item(item_id, fatura_id)
        self.item_repo.remover(item)
        self.db.commit()

    def listar_tributos(
        self, fatura_id: uuid.UUID, ator: UsuarioAutenticado
    ) -> list[TributoFaturaOut]:
        self._verificar_acesso_fatura(fatura_id, ator, exigir_edicao=False)
        return [TributoFaturaOut.model_validate(t) for t in self.tributo_repo.listar(fatura_id)]

    def criar_tributo(
        self, fatura_id: uuid.UUID, dados: TributoFaturaCreate, ator: UsuarioAutenticado
    ) -> TributoFaturaOut:
        self._verificar_acesso_fatura(fatura_id, ator, exigir_edicao=True)
        try:
            tributo = self.tributo_repo.criar(fatura_id, dados)
            self.db.commit()
            self.db.refresh(tributo)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflitoDuplicidadeError("Este tributo já existe para a fatura.") from exc
        return TributoFaturaOut.model_validate(tributo)

    def atualizar_tributo(
        self,
        fatura_id: uuid.UUID,
        tributo_id: uuid.UUID,
        dados: TributoFaturaUpdate,
        ator: UsuarioAutenticado,
    ) -> TributoFaturaOut:
        self._verificar_acesso_fatura(fatura_id, ator, exigir_edicao=True)
        tributo = self._obter_tributo(tributo_id, fatura_id)
        try:
            self.tributo_repo.atualizar(tributo, dados)
            self.db.commit()
            self.db.refresh(tributo)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflitoDuplicidadeError("Este tributo já existe para a fatura.") from exc
        return TributoFaturaOut.model_validate(tributo)

    def deletar_tributo(
        self, fatura_id: uuid.UUID, tributo_id: uuid.UUID, ator: UsuarioAutenticado
    ) -> None:
        self._verificar_acesso_fatura(fatura_id, ator, exigir_edicao=True)
        tributo = self._obter_tributo(tributo_id, fatura_id)
        self.tributo_repo.remover(tributo)
        self.db.commit()

    def _obter_orm(self, id: uuid.UUID, detalhe: bool = False) -> Fatura:
        fatura = self.repo.buscar_por_id(id, detalhe=detalhe)
        if fatura is None:
            raise NaoEncontradoError("Fatura não encontrada.")
        return fatura

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

    def _validar_documento(
        self, documento_id: uuid.UUID | None, uc_id: uuid.UUID
    ) -> DocumentoBruto | None:
        if documento_id is None:
            return None
        documento = self.db.get(DocumentoBruto, documento_id)
        if documento is None or documento.unidade_consumidora_id != uc_id:
            raise RegraVioladaError("Documento bruto não pertence à unidade consumidora.")
        return documento

    def _validar_total(self, dados: FaturaCreate) -> None:
        if not dados.itens and not dados.tributos:
            return
        total_componentes = sum((i.valor for i in dados.itens), Decimal("0"))
        total_componentes += sum((t.valor for t in dados.tributos), Decimal("0"))
        if abs(total_componentes - dados.valor_total) > TOLERANCIA_TOTAL:
            raise RegraVioladaError(
                "Soma de itens e tributos diverge do valor_total acima da tolerância de centavos."
            )

    def _verificar_acesso_fatura(
        self, fatura_id: uuid.UUID, ator: UsuarioAutenticado, exigir_edicao: bool
    ) -> Fatura:
        fatura = self._obter_orm(fatura_id)
        uc = self._obter_uc(fatura.unidade_consumidora_id)
        self._verificar_acesso_uc(uc, ator, exigir_edicao=exigir_edicao)
        return fatura

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
            raise AcessoNegadoError("Você não tem permissão para alterar faturas desta UC.")
        return acesso

    def _obter_medida(self, medida_id: uuid.UUID, fatura_id: uuid.UUID) -> MedidaFatura:
        medida = self.medida_repo.buscar_por_id(medida_id)
        if medida is None or medida.fatura_id != fatura_id:
            raise NaoEncontradoError("Medida da fatura não encontrada.")
        return medida

    def _obter_item(self, item_id: uuid.UUID, fatura_id: uuid.UUID) -> ItemFatura:
        item = self.item_repo.buscar_por_id(item_id)
        if item is None or item.fatura_id != fatura_id:
            raise NaoEncontradoError("Item da fatura não encontrado.")
        return item

    def _obter_tributo(self, tributo_id: uuid.UUID, fatura_id: uuid.UUID) -> TributoFatura:
        tributo = self.tributo_repo.buscar_por_id(tributo_id)
        if tributo is None or tributo.fatura_id != fatura_id:
            raise NaoEncontradoError("Tributo da fatura não encontrado.")
        return tributo
