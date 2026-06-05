import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.app.domains.auditoria.models import Achado, ExecucaoValidacao
from src.app.domains.auditoria.schemas import AchadoCreate, AchadoUpdate


class ExecucaoValidacaoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def criar(self, execucao: ExecucaoValidacao) -> ExecucaoValidacao:
        self.db.add(execucao)
        self.db.flush()
        return execucao

    def buscar_por_id(self, id: uuid.UUID, detalhe: bool = False) -> ExecucaoValidacao | None:
        if not detalhe:
            return self.db.get(ExecucaoValidacao, id)
        stmt = (
            select(ExecucaoValidacao)
            .where(ExecucaoValidacao.id == id)
            .options(
                selectinload(ExecucaoValidacao.resultados),
                selectinload(ExecucaoValidacao.achados),
            )
        )
        return self.db.scalar(stmt)

    def listar_por_fatura(self, fatura_id: uuid.UUID) -> list[ExecucaoValidacao]:
        return list(
            self.db.scalars(
                select(ExecucaoValidacao)
                .where(ExecucaoValidacao.fatura_id == fatura_id)
                .order_by(ExecucaoValidacao.iniciado_em.desc())
            ).all()
        )


class AchadoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def criar(self, dados: AchadoCreate) -> Achado:
        achado = Achado(**dados.model_dump())
        self.db.add(achado)
        self.db.flush()
        return achado

    def listar(
        self,
        fatura_id: uuid.UUID | None = None,
        status=None,
    ) -> list[Achado]:
        stmt = select(Achado).order_by(Achado.criado_em.desc())
        if fatura_id is not None:
            stmt = stmt.where(Achado.fatura_id == fatura_id)
        if status is not None:
            stmt = stmt.where(Achado.status == status)
        return list(self.db.scalars(stmt).all())

    def buscar_por_id(self, id: uuid.UUID) -> Achado | None:
        return self.db.get(Achado, id)

    def atualizar(self, achado: Achado, dados: AchadoUpdate) -> None:
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(achado, campo, valor)
        self.db.flush()

    def remover(self, achado: Achado) -> None:
        self.db.delete(achado)
        self.db.flush()
