import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.app.domains.recuperacao.models import CasoRecuperacao, ItemRecuperacao
from src.app.domains.recuperacao.schemas import (
    CasoRecuperacaoCreate,
    CasoRecuperacaoUpdate,
    ItemRecuperacaoCreate,
    ItemRecuperacaoUpdate,
)


class CasoRecuperacaoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def criar(
        self,
        dados: CasoRecuperacaoCreate,
        criado_por_id: uuid.UUID,
        numero_caso: str,
    ) -> CasoRecuperacao:
        base = dados.model_dump(exclude={"numero_caso"})
        caso = CasoRecuperacao(**base, criado_por_id=criado_por_id, numero_caso=numero_caso)
        self.db.add(caso)
        self.db.flush()
        return caso

    def listar(
        self,
        cliente_id: uuid.UUID | None = None,
        unidade_consumidora_id: uuid.UUID | None = None,
        status=None,
    ) -> list[CasoRecuperacao]:
        stmt = select(CasoRecuperacao).order_by(CasoRecuperacao.aberto_em.desc())
        if cliente_id is not None:
            stmt = stmt.where(CasoRecuperacao.cliente_id == cliente_id)
        if unidade_consumidora_id is not None:
            stmt = stmt.where(CasoRecuperacao.unidade_consumidora_id == unidade_consumidora_id)
        if status is not None:
            stmt = stmt.where(CasoRecuperacao.status == status)
        return list(self.db.scalars(stmt).all())

    def buscar_por_id(self, id: uuid.UUID, detalhe: bool = False) -> CasoRecuperacao | None:
        if not detalhe:
            return self.db.get(CasoRecuperacao, id)
        stmt = (
            select(CasoRecuperacao)
            .where(CasoRecuperacao.id == id)
            .options(selectinload(CasoRecuperacao.itens))
        )
        return self.db.scalar(stmt)

    def atualizar(self, caso: CasoRecuperacao, dados: CasoRecuperacaoUpdate) -> None:
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(caso, campo, valor)
        self.db.flush()

    def recalcular_totais(self, caso: CasoRecuperacao) -> None:
        itens = self.db.scalars(
            select(ItemRecuperacao).where(ItemRecuperacao.caso_recuperacao_id == caso.id)
        ).all()
        caso.total_estimado = sum((i.valor_cobrado_a_maior for i in itens), Decimal("0"))
        caso.total_recuperavel = sum((i.valor_recuperavel for i in itens), Decimal("0"))
        caso.total_reconhecido = sum((i.valor_reconhecido for i in itens), Decimal("0"))
        caso.total_devolvido = sum((i.valor_devolvido for i in itens), Decimal("0"))
        self.db.flush()

    def remover(self, caso: CasoRecuperacao) -> None:
        self.db.delete(caso)
        self.db.flush()


class ItemRecuperacaoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def criar(self, caso_id: uuid.UUID, dados: ItemRecuperacaoCreate) -> ItemRecuperacao:
        payload = dados.model_dump()
        if payload["valor_recuperavel"] is None:
            payload["valor_recuperavel"] = payload["valor_cobrado_a_maior"]
        item = ItemRecuperacao(caso_recuperacao_id=caso_id, **payload)
        self.db.add(item)
        self.db.flush()
        return item

    def listar_por_caso(self, caso_id: uuid.UUID) -> list[ItemRecuperacao]:
        return list(
            self.db.scalars(
                select(ItemRecuperacao).where(ItemRecuperacao.caso_recuperacao_id == caso_id)
            ).all()
        )

    def buscar_por_id(self, id: uuid.UUID) -> ItemRecuperacao | None:
        return self.db.get(ItemRecuperacao, id)

    def atualizar(self, item: ItemRecuperacao, dados: ItemRecuperacaoUpdate) -> None:
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(item, campo, valor)
        self.db.flush()

    def remover(self, item: ItemRecuperacao) -> None:
        self.db.delete(item)
        self.db.flush()
