import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.app.domains.clientes.models import AcessoCliente, UnidadeConsumidora
from src.app.domains.faturas.models import Fatura, ItemFatura, MedidaFatura, TributoFatura
from src.app.domains.faturas.schemas import (
    FaturaCreate,
    FaturaUpdate,
    ItemFaturaCreate,
    ItemFaturaUpdate,
    MedidaFaturaCreate,
    MedidaFaturaUpdate,
    TributoFaturaCreate,
    TributoFaturaUpdate,
)


class FaturaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def criar(self, dados: FaturaCreate) -> Fatura:
        base = dados.model_dump(exclude={"medidas", "itens", "tributos"})
        fatura = Fatura(**base)
        fatura.medidas = [MedidaFatura(**m.model_dump()) for m in dados.medidas]
        fatura.itens = [ItemFatura(**i.model_dump()) for i in dados.itens]
        fatura.tributos = [TributoFatura(**t.model_dump()) for t in dados.tributos]
        self.db.add(fatura)
        self.db.flush()
        return fatura

    def listar(
        self,
        usuario_id: uuid.UUID | None = None,
        apenas_acessiveis: bool = False,
        unidade_consumidora_id: uuid.UUID | None = None,
        lote_auditoria_id: uuid.UUID | None = None,
        competencia: str | None = None,
    ) -> list[Fatura]:
        stmt = select(Fatura)
        if apenas_acessiveis and usuario_id is not None:
            stmt = (
                stmt.join(
                    UnidadeConsumidora,
                    UnidadeConsumidora.id == Fatura.unidade_consumidora_id,
                )
                .join(AcessoCliente, AcessoCliente.cliente_id == UnidadeConsumidora.cliente_id)
                .where(AcessoCliente.usuario_id == usuario_id)
            )
        if unidade_consumidora_id is not None:
            stmt = stmt.where(Fatura.unidade_consumidora_id == unidade_consumidora_id)
        if lote_auditoria_id is not None:
            stmt = stmt.where(Fatura.lote_auditoria_id == lote_auditoria_id)
        if competencia is not None:
            stmt = stmt.where(Fatura.competencia == competencia)
        stmt = stmt.order_by(Fatura.competencia.desc(), Fatura.criada_em.desc())
        return list(self.db.scalars(stmt).all())

    def buscar_por_id(self, id: uuid.UUID, detalhe: bool = False) -> Fatura | None:
        if not detalhe:
            return self.db.get(Fatura, id)
        stmt = (
            select(Fatura)
            .where(Fatura.id == id)
            .options(
                selectinload(Fatura.medidas),
                selectinload(Fatura.itens),
                selectinload(Fatura.tributos),
            )
        )
        return self.db.scalar(stmt)

    def atualizar(self, fatura: Fatura, dados: FaturaUpdate) -> None:
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(fatura, campo, valor)
        self.db.flush()

    def remover(self, fatura: Fatura) -> None:
        self.db.delete(fatura)
        self.db.flush()


class MedidaFaturaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def criar(self, fatura_id: uuid.UUID, dados: MedidaFaturaCreate) -> MedidaFatura:
        medida = MedidaFatura(fatura_id=fatura_id, **dados.model_dump())
        self.db.add(medida)
        self.db.flush()
        return medida

    def listar(self, fatura_id: uuid.UUID) -> list[MedidaFatura]:
        return list(
            self.db.scalars(
                select(MedidaFatura)
                .where(MedidaFatura.fatura_id == fatura_id)
                .order_by(MedidaFatura.posto_horario)
            ).all()
        )

    def buscar_por_id(self, id: uuid.UUID) -> MedidaFatura | None:
        return self.db.get(MedidaFatura, id)

    def atualizar(self, medida: MedidaFatura, dados: MedidaFaturaUpdate) -> None:
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(medida, campo, valor)
        self.db.flush()

    def remover(self, medida: MedidaFatura) -> None:
        self.db.delete(medida)
        self.db.flush()


class ItemFaturaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def criar(self, fatura_id: uuid.UUID, dados: ItemFaturaCreate) -> ItemFatura:
        item = ItemFatura(fatura_id=fatura_id, **dados.model_dump())
        self.db.add(item)
        self.db.flush()
        return item

    def listar(self, fatura_id: uuid.UUID) -> list[ItemFatura]:
        return list(
            self.db.scalars(
                select(ItemFatura)
                .where(ItemFatura.fatura_id == fatura_id)
                .order_by(ItemFatura.ordem, ItemFatura.id)
            ).all()
        )

    def buscar_por_id(self, id: uuid.UUID) -> ItemFatura | None:
        return self.db.get(ItemFatura, id)

    def atualizar(self, item: ItemFatura, dados: ItemFaturaUpdate) -> None:
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(item, campo, valor)
        self.db.flush()

    def remover(self, item: ItemFatura) -> None:
        self.db.delete(item)
        self.db.flush()


class TributoFaturaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def criar(self, fatura_id: uuid.UUID, dados: TributoFaturaCreate) -> TributoFatura:
        tributo = TributoFatura(fatura_id=fatura_id, **dados.model_dump())
        self.db.add(tributo)
        self.db.flush()
        return tributo

    def listar(self, fatura_id: uuid.UUID) -> list[TributoFatura]:
        return list(
            self.db.scalars(
                select(TributoFatura)
                .where(TributoFatura.fatura_id == fatura_id)
                .order_by(TributoFatura.tipo_tributo)
            ).all()
        )

    def buscar_por_id(self, id: uuid.UUID) -> TributoFatura | None:
        return self.db.get(TributoFatura, id)

    def atualizar(self, tributo: TributoFatura, dados: TributoFaturaUpdate) -> None:
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(tributo, campo, valor)
        self.db.flush()

    def remover(self, tributo: TributoFatura) -> None:
        self.db.delete(tributo)
        self.db.flush()
