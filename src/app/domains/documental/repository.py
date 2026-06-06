import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.core.enums import StatusExtracao
from src.app.domains.clientes.models import AcessoCliente, UnidadeConsumidora
from src.app.domains.documental.models import DocumentoBruto, LayoutFatura
from src.app.domains.documental.schemas import (
    DocumentoBrutoCreate,
    DocumentoBrutoUpdate,
    LayoutFaturaCreate,
    LayoutFaturaUpdate,
)


class LayoutFaturaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def criar(self, dados: LayoutFaturaCreate) -> LayoutFatura:
        layout = LayoutFatura(**dados.model_dump())
        self.db.add(layout)
        self.db.flush()
        return layout

    def listar(self, distribuidora_id: uuid.UUID | None = None) -> list[LayoutFatura]:
        stmt = select(LayoutFatura).order_by(LayoutFatura.codigo)
        if distribuidora_id is not None:
            stmt = stmt.where(LayoutFatura.distribuidora_id == distribuidora_id)
        return list(self.db.scalars(stmt).all())

    def buscar_por_id(self, id: uuid.UUID) -> LayoutFatura | None:
        return self.db.get(LayoutFatura, id)

    def atualizar(self, layout: LayoutFatura, dados: LayoutFaturaUpdate) -> None:
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(layout, campo, valor)
        self.db.flush()

    def desativar(self, layout: LayoutFatura) -> None:
        layout.ativo = False
        self.db.flush()

    def remover(self, layout: LayoutFatura) -> None:
        self.db.delete(layout)
        self.db.flush()


class DocumentoBrutoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def criar(self, dados: DocumentoBrutoCreate, enviado_por_id: uuid.UUID) -> DocumentoBruto:
        documento = DocumentoBruto(
            **dados.model_dump(),
            enviado_por_id=enviado_por_id,
            status_extracao=StatusExtracao.PENDENTE,
        )
        self.db.add(documento)
        self.db.flush()
        return documento

    def listar(
        self,
        usuario_id: uuid.UUID | None = None,
        apenas_acessiveis: bool = False,
        unidade_consumidora_id: uuid.UUID | None = None,
        lote_auditoria_id: uuid.UUID | None = None,
        status_extracao: StatusExtracao | None = None,
    ) -> list[DocumentoBruto]:
        stmt = select(DocumentoBruto)
        if apenas_acessiveis and usuario_id is not None:
            stmt = (
                stmt.join(
                    UnidadeConsumidora,
                    UnidadeConsumidora.id == DocumentoBruto.unidade_consumidora_id,
                )
                .join(AcessoCliente, AcessoCliente.cliente_id == UnidadeConsumidora.cliente_id)
                .where(AcessoCliente.usuario_id == usuario_id)
            )
        if unidade_consumidora_id is not None:
            stmt = stmt.where(DocumentoBruto.unidade_consumidora_id == unidade_consumidora_id)
        if lote_auditoria_id is not None:
            stmt = stmt.where(DocumentoBruto.lote_auditoria_id == lote_auditoria_id)
        if status_extracao is not None:
            stmt = stmt.where(DocumentoBruto.status_extracao == status_extracao)
        stmt = stmt.order_by(DocumentoBruto.enviado_em.desc())
        return list(self.db.scalars(stmt).all())

    def buscar_por_id(self, id: uuid.UUID) -> DocumentoBruto | None:
        return self.db.get(DocumentoBruto, id)

    def buscar_por_sha256(self, sha256: str) -> DocumentoBruto | None:
        return self.db.scalar(
            select(DocumentoBruto).where(DocumentoBruto.sha256 == sha256.lower())
        )

    def atualizar(self, documento: DocumentoBruto, dados: DocumentoBrutoUpdate) -> None:
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(documento, campo, valor)
        self.db.flush()

    def remover(self, documento: DocumentoBruto) -> None:
        self.db.delete(documento)
        self.db.flush()
