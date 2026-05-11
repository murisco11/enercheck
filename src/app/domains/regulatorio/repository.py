import uuid
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.app.domains.regulatorio.models import (
    ChunkRegulatorio,
    DocumentoRegulatorio,
    PacoteRegras,
    RegraValidacao,
    SnapshotTarifa,
)


class DocumentoRegulatorioRepository:
    def __init__(self, session: Session):
        self._s = session

    def criar(self, doc: DocumentoRegulatorio) -> DocumentoRegulatorio:
        self._s.add(doc)
        self._s.flush()
        return doc

    def buscar_por_id(self, doc_id: uuid.UUID) -> DocumentoRegulatorio | None:
        return self._s.get(DocumentoRegulatorio, doc_id)

    def listar(self) -> list[DocumentoRegulatorio]:
        return list(self._s.execute(select(DocumentoRegulatorio)).scalars().all())

    def desativar(self, doc: DocumentoRegulatorio) -> None:
        doc.ativo = False
        self._s.flush()

    def remover(self, doc: DocumentoRegulatorio) -> None:
        self._s.delete(doc)
        self._s.flush()


class ChunkRegulatorioRepository:
    def __init__(self, session: Session):
        self._s = session

    def criar_lote(self, chunks: list[ChunkRegulatorio]) -> None:
        self._s.add_all(chunks)
        self._s.flush()

    def atualizar_embedding(self, chunk_id: uuid.UUID, embedding: list[float]) -> None:
        chunk = self._s.get(ChunkRegulatorio, chunk_id)
        if chunk:
            chunk.embedding = embedding
            self._s.flush()

    def buscar_similares(
        self,
        embedding: list[float],
        top_k: int = 5,
        documento_id: uuid.UUID | None = None,
    ) -> list[tuple[ChunkRegulatorio, float]]:
        distancia = ChunkRegulatorio.embedding.cosine_distance(embedding)
        stmt = (
            select(ChunkRegulatorio, (1 - distancia).label("similaridade"))
            .where(ChunkRegulatorio.embedding.is_not(None))
            .order_by(distancia)
            .limit(top_k)
        )
        if documento_id:
            stmt = stmt.where(ChunkRegulatorio.documento_regulatorio_id == documento_id)
        result = self._s.execute(stmt)
        return [(row[0], float(row[1])) for row in result.all()]

    def listar_por_documento(self, documento_id: uuid.UUID) -> list[ChunkRegulatorio]:
        return list(
            self._s.execute(
                select(ChunkRegulatorio)
                .where(ChunkRegulatorio.documento_regulatorio_id == documento_id)
                .order_by(ChunkRegulatorio.indice)
            )
            .scalars()
            .all()
        )


class SnapshotTarifaRepository:
    def __init__(self, session: Session):
        self._s = session

    def criar(self, snap: SnapshotTarifa) -> SnapshotTarifa:
        self._s.add(snap)
        self._s.flush()
        return snap

    def desativar(self, snap: SnapshotTarifa) -> None:
        snap.ativo = False
        self._s.flush()

    def remover(self, snap: SnapshotTarifa) -> None:
        self._s.delete(snap)
        self._s.flush()

    def buscar_vigente(
        self, distribuidora_id: uuid.UUID, data_referencia: date
    ) -> list[SnapshotTarifa]:
        stmt = (
            select(SnapshotTarifa)
            .where(SnapshotTarifa.distribuidora_id == distribuidora_id)
            .where(SnapshotTarifa.vigencia_inicio <= data_referencia)
            .where(
                or_(
                    SnapshotTarifa.vigencia_fim.is_(None),
                    SnapshotTarifa.vigencia_fim >= data_referencia,
                )
            )
        )
        return list(self._s.execute(stmt).scalars().all())


class PacoteRegrasRepository:
    def __init__(self, session: Session):
        self._s = session

    def criar(self, pacote: PacoteRegras) -> PacoteRegras:
        self._s.add(pacote)
        self._s.flush()
        return pacote

    def buscar_vigente(self) -> PacoteRegras | None:
        return self._s.execute(
            select(PacoteRegras).where(PacoteRegras.vigente.is_(True)).limit(1)
        ).scalar_one_or_none()

    def listar(self) -> list[PacoteRegras]:
        return list(self._s.execute(select(PacoteRegras)).scalars().all())

    def desativar(self, pacote: PacoteRegras) -> None:
        pacote.ativo = False
        self._s.flush()

    def remover(self, pacote: PacoteRegras) -> None:
        self._s.delete(pacote)
        self._s.flush()


class RegraValidacaoRepository:
    def __init__(self, session: Session):
        self._s = session

    def criar(self, regra: RegraValidacao) -> RegraValidacao:
        self._s.add(regra)
        self._s.flush()
        return regra

    def buscar_por_id(self, regra_id: uuid.UUID) -> RegraValidacao | None:
        return self._s.get(RegraValidacao, regra_id)

    def desativar(self, regra: RegraValidacao) -> None:
        regra.ativa = False
        self._s.flush()

    def remover(self, regra: RegraValidacao) -> None:
        self._s.delete(regra)
        self._s.flush()

    def listar_por_pacote(
        self, pacote_id: uuid.UUID, apenas_ativas: bool = True
    ) -> list[RegraValidacao]:
        stmt = select(RegraValidacao).where(RegraValidacao.pacote_regras_id == pacote_id)
        if apenas_ativas:
            stmt = stmt.where(RegraValidacao.ativa.is_(True))
        return list(self._s.execute(stmt).scalars().all())
