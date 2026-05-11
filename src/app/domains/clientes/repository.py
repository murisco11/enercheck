import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from src.app.domains.clientes.models import (
    AcessoCliente,
    Cliente,
    Distribuidora,
    LoteAuditoria,
    UnidadeConsumidora,
)
from src.app.domains.clientes.schemas import (
    ClienteCreate,
    ClienteUpdate,
    DistribuidoraCreate,
    LoteCreate,
    LoteUpdate,
    PaginacaoKeyset,
    UnidadeConsumidoraCreate,
    UnidadeConsumidoraUpdate,
)


class DistribuidoraRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def criar(self, dados: DistribuidoraCreate) -> Distribuidora:
        dist = Distribuidora(
            razao_social=dados.razao_social,
            cnpj=dados.cnpj,
            sigla=dados.sigla,
            estado=dados.estado,
        )
        self.db.add(dist)
        self.db.flush()
        return dist

    def listar(self) -> list[Distribuidora]:
        return list(self.db.scalars(select(Distribuidora).order_by(Distribuidora.sigla)).all())

    def buscar_por_id(self, id: uuid.UUID) -> Distribuidora | None:
        return self.db.get(Distribuidora, id)

    def desativar(self, dist: Distribuidora) -> None:
        dist.ativo = False
        self.db.flush()

    def remover(self, dist: Distribuidora) -> None:
        self.db.delete(dist)
        self.db.flush()


class ClienteRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def criar(self, dados: ClienteCreate) -> Cliente:
        cliente = Cliente(
            razao_social=dados.razao_social,
            nome_fantasia=dados.nome_fantasia,
            cnpj=dados.cnpj,
            ativo=True,
        )
        self.db.add(cliente)
        self.db.flush()
        return cliente

    def listar_todos(self) -> list[Cliente]:
        return list(self.db.scalars(select(Cliente).order_by(Cliente.razao_social)).all())

    def listar_por_usuario(self, usuario_id: uuid.UUID) -> list[Cliente]:
        stmt = (
            select(Cliente)
            .join(AcessoCliente, AcessoCliente.cliente_id == Cliente.id)
            .where(AcessoCliente.usuario_id == usuario_id)
            .order_by(Cliente.razao_social)
        )
        return list(self.db.scalars(stmt).all())

    def buscar_por_id(self, id: uuid.UUID) -> Cliente | None:
        return self.db.get(Cliente, id)

    def atualizar(self, cliente: Cliente, dados: ClienteUpdate) -> None:
        if dados.razao_social is not None:
            cliente.razao_social = dados.razao_social
        if dados.nome_fantasia is not None:
            cliente.nome_fantasia = dados.nome_fantasia
        self.db.flush()

    def count(self) -> int:
        return int(self.db.scalar(select(func.count()).select_from(Cliente)) or 0)

    def desativar(self, cliente: Cliente) -> None:
        cliente.ativo = False
        self.db.flush()

    def remover(self, cliente: Cliente) -> None:
        self.db.delete(cliente)
        self.db.flush()


class AcessoClienteRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def buscar(self, usuario_id: uuid.UUID, cliente_id: uuid.UUID) -> AcessoCliente | None:
        return self.db.scalar(
            select(AcessoCliente).where(
                AcessoCliente.usuario_id == usuario_id,
                AcessoCliente.cliente_id == cliente_id,
            )
        )

    def criar(
        self, usuario_id: uuid.UUID, cliente_id: uuid.UUID, pode_editar: bool = False
    ) -> AcessoCliente:
        acesso = AcessoCliente(
            usuario_id=usuario_id,
            cliente_id=cliente_id,
            pode_editar=pode_editar,
        )
        self.db.add(acesso)
        self.db.flush()
        return acesso


class UnidadeConsumidoraRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def criar(self, cliente_id: uuid.UUID, dados: UnidadeConsumidoraCreate) -> UnidadeConsumidora:
        uc = UnidadeConsumidora(
            cliente_id=cliente_id,
            distribuidora_id=dados.distribuidora_id,
            codigo_instalacao=dados.codigo_instalacao,
            codigo_cliente=dados.codigo_cliente,
            grupo=dados.grupo,
            subgrupo=dados.subgrupo,
            modalidade=dados.modalidade,
            tarifa_social=dados.tarifa_social,
            cidade=dados.cidade,
            estado=dados.estado,
        )
        self.db.add(uc)
        self.db.flush()
        return uc

    def listar_por_cliente(self, cliente_id: uuid.UUID) -> list[UnidadeConsumidora]:
        return list(
            self.db.scalars(
                select(UnidadeConsumidora)
                .where(UnidadeConsumidora.cliente_id == cliente_id)
                .order_by(UnidadeConsumidora.codigo_instalacao)
            ).all()
        )

    def buscar_por_id(self, id: uuid.UUID) -> UnidadeConsumidora | None:
        return self.db.get(UnidadeConsumidora, id)

    def atualizar(self, uc: UnidadeConsumidora, dados: UnidadeConsumidoraUpdate) -> None:
        if dados.codigo_instalacao is not None:
            uc.codigo_instalacao = dados.codigo_instalacao
        if dados.codigo_cliente is not None:
            uc.codigo_cliente = dados.codigo_cliente
        if dados.grupo is not None:
            uc.grupo = dados.grupo
        if dados.subgrupo is not None:
            uc.subgrupo = dados.subgrupo
        if dados.modalidade is not None:
            uc.modalidade = dados.modalidade
        if dados.tarifa_social is not None:
            uc.tarifa_social = dados.tarifa_social
        if dados.cidade is not None:
            uc.cidade = dados.cidade
        if dados.estado is not None:
            uc.estado = dados.estado
        self.db.flush()

    def count_por_cliente(self, cliente_id: uuid.UUID) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(UnidadeConsumidora)
                .where(UnidadeConsumidora.cliente_id == cliente_id)
            )
            or 0
        )

    def desativar(self, uc: UnidadeConsumidora) -> None:
        uc.ativo = False
        self.db.flush()

    def remover(self, uc: UnidadeConsumidora) -> None:
        self.db.delete(uc)
        self.db.flush()


class LoteRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def criar(
        self, dados: LoteCreate, criado_por_id: uuid.UUID
    ) -> LoteAuditoria:
        lote = LoteAuditoria(
            unidade_consumidora_id=dados.unidade_consumidora_id,
            criado_por_id=criado_por_id,
            rotulo=dados.rotulo,
            competencia_inicio=dados.competencia_inicio,
            competencia_fim=dados.competencia_fim,
        )
        self.db.add(lote)
        self.db.flush()
        return lote

    def listar(
        self,
        pag: PaginacaoKeyset,
        uc_id: uuid.UUID | None = None,
        usuario_id: uuid.UUID | None = None,
        apenas_acessiveis: bool = False,
    ) -> list[LoteAuditoria]:
        stmt = select(LoteAuditoria)
        if uc_id is not None:
            stmt = stmt.where(LoteAuditoria.unidade_consumidora_id == uc_id)
        if apenas_acessiveis and usuario_id is not None:
            stmt = stmt.join(
                UnidadeConsumidora,
                UnidadeConsumidora.id == LoteAuditoria.unidade_consumidora_id,
            ).join(
                AcessoCliente,
                AcessoCliente.cliente_id == UnidadeConsumidora.cliente_id,
            ).where(
                AcessoCliente.usuario_id == usuario_id
            )
        if pag.after_id is not None:
            stmt = stmt.where(LoteAuditoria.id > pag.after_id)
        stmt = stmt.order_by(LoteAuditoria.id).limit(pag.limite + 1)
        return list(self.db.scalars(stmt).all())

    def buscar_por_id(self, id: uuid.UUID) -> LoteAuditoria | None:
        return self.db.get(LoteAuditoria, id)

    def atualizar(
        self,
        lote: LoteAuditoria,
        dados: LoteUpdate,
        pode_alterar_status: bool,
    ) -> None:
        if dados.rotulo is not None:
            lote.rotulo = dados.rotulo
        if dados.status is not None and pode_alterar_status:
            lote.status = dados.status
        self.db.flush()

    def desativar(self, lote: LoteAuditoria) -> None:
        lote.ativo = False
        self.db.flush()

    def remover(self, lote: LoteAuditoria) -> None:
        self.db.delete(lote)
        self.db.flush()
